import asyncio
import random
import time
import unicodedata
import httpx
from datetime import datetime
from typing import List, Tuple

import httpx
from fastapi import HTTPException

from config import (
    CACHE_TTL_SECONDS,
    GEMINI_API_KEY,
    GEMINI_API_KEYS,
    GEMINI_COOLDOWN_SECONDS,
    GEMINI_FALLBACK_MODELS,
    GEMINI_KEY_COOLDOWN_SECONDS,
    GEMINI_MODEL,
    GOOGLE_SHEET_API_URL,
    OFFICIAL_SOURCE_URL,
    PROMPT,
)
from utils import (
    append_video_to_answer,
    catalog_major,
    extract_combinations_from_context,
    find_context,
    normalize_source_line,
    snippets,
    source_names,
    _fold,
)

GEMINI_COOLDOWN_UNTIL = 0.0
ANSWER_CACHE = {}
KEY_COOLDOWN_UNTIL = {}
_KEY_ROTATION_INDEX = 0
_KEY_ROTATION_LOCK = asyncio.Lock()
SESSION_MAJOR_MEMORY = {}
SESSION_CHAT_HISTORY = {}

# Chuẩn hóa câu trả lời lại 
def _cache_key(question: str) -> str:
    return _fold(question).strip()


def _cache_get(question: str) -> str:
    # TTL cache: trả kết quả cũ nếu còn hạn, tự dọn nếu đã hết hạn.
    key = _cache_key(question)
    item = ANSWER_CACHE.get(key)
    if not item: #neu ko co  cache thi tra ve rong
        return ""
    expires_at, answer = item #lay thoi gian het han va cau tra loi
    if expires_at < time.time(): #neu thoi gian het han nho hon thoi gian hien tai thi xoa cache
        ANSWER_CACHE.pop(key, None) #xoa cache
        return ""  #tra ve rong
    return answer #tra ve cau tra loi


def _cache_set(question: str, answer: str) -> None: #luu cache
    ANSWER_CACHE[_cache_key(question)] = (time.time() + CACHE_TTL_SECONDS, answer) #luu cache thoi diem hien tai va thoi diem het han


def _gemini_in_cooldown() -> bool:#kiem tra xem gemini co trong thoi gian cooldown khong
    # Chặn gọi Gemini trong khoảng cooldown sau khi dính quota 429.
    return time.time() < GEMINI_COOLDOWN_UNTIL #neu thoi gian hien tai nho hon thoi gian het han thi tra ve true


def _start_gemini_cooldown():#bat dau thoi gian cooldown
    global GEMINI_COOLDOWN_UNTIL#bien toan cuc
    GEMINI_COOLDOWN_UNTIL = time.time() + GEMINI_COOLDOWN_SECONDS#thoi gian hien tai cong voi thoi gian cooldown


def _mark_key_cooldown(api_key: str) -> None:#danh dau key bi cooldown
    # Mỗi key bị quota sẽ bị nghỉ riêng, tránh gọi lặp vào key đang nghẽn.
    KEY_COOLDOWN_UNTIL[api_key] = time.time() + GEMINI_KEY_COOLDOWN_SECONDS#    thoi gian hien tai cong voi thoi gian cooldown


def _key_available(api_key: str) -> bool:#kiem tra xem key co kha dung khong
    return time.time() >= KEY_COOLDOWN_UNTIL.get(api_key, 0.0)#neu thoi gian hien tai nho hon thoi gian het han thi tra ve true


async def _next_available_keys() -> List[str]:#lay danh sach key kha dung trong .env
    # Round-robin thông minh: xoay điểm bắt đầu mỗi request và bỏ key đang cooldown.
    global _KEY_ROTATION_INDEX#bien toan cuc
    async with _KEY_ROTATION_LOCK:#khoa de tranh truy cap cung luc
        keys = GEMINI_API_KEYS if GEMINI_API_KEYS else ([GEMINI_API_KEY] if GEMINI_API_KEY else [])#lay danh sach key
        keys = [k for k in keys if k]#lay danh sach key khong trung lap
        if not keys:#neu khong co key nao
            return []#tra ve rong

        start = _KEY_ROTATION_INDEX % len(keys)#lay diem bat dau
        ordered = keys[start:] + keys[:start]#sap xep danh sach key cat lít tai vi tri rui ghep lai
        _KEY_ROTATION_INDEX = (_KEY_ROTATION_INDEX + 1) % len(keys)#tang diem bat dau len de lan sau lay key khac

    return [k for k in ordered if _key_available(k)]#lay danh sach key kha dung

# jitter_ratio ti le do random,_backoff_with_jitter ham tinh thoi gian 
def _backoff_with_jitter(attempt: int, base_delay: float = 0.8, cap: float = 8.0, jitter_ratio: float = 0.4) -> float:#tinh thoi gian delay de tranh request don cum khi retry
    # Exponential backoff + jitter để giảm request dồn cụm khi retry.
    exp_delay = min(cap, base_delay * (2 ** max(0, attempt - 1)))#delay tang theo so nhan 2 nhung ko duoc vuot qua cap gioi han toi da 8s
    jitter = exp_delay * jitter_ratio * random.random()#them do ngau nhien vao delay tranh retry hang loat
    return exp_delay + jitter#tra ve delay


async def call_gemini(question: str, context: List[str], chat_history: List[dict] = None) -> Tuple[str, str, str]: #ham goi gemini
    if chat_history is None:
        chat_history = []
    
    keys_to_try = await _next_available_keys() #lay danh sach key kha dung
    if not keys_to_try:
        raise HTTPException(status_code=429, detail="No available Gemini API key") #tra ve ko co key nao kha dung o 429

    context_text = "\n\n".join(context[:8]) if context else "Không có dữ liệu tuyển sinh."
    prompt = PROMPT.format(context_text=context_text, question=question)

    # Ưu tiên model chính, sau đó fallback; loại trùng để không gọi lặp vô ích.
    models_to_try = [] #tao danh sach model
    for m in [GEMINI_MODEL] + GEMINI_FALLBACK_MODELS: #lay model chinh va model du phong
        if m and m not in models_to_try: #neu model ton tai va chua co trong danh sach
            models_to_try.append(m) #them model vao danh sach

    last_error = "Gemini error" #thong bao loi gemini
    saw_quota_error = False #kiem tra xem co loi quota khong
    max_attempts_per_model = 2 #so lan thu toi da cho moi model la 2
    #AsyncClient : cho phep goi api ko dong bo 
    async with httpx.AsyncClient(timeout=30) as client: #tao client de goi api dung httpx goi api  neu qua 30s tra ve ngheo
        # Xoay vòng theo key trước, trong mỗi key mới fallback theo model.
        for api_key in keys_to_try: #duyet qua danh sach key kha dung
            model_quota_count = 0 # đếm số model bị quota trên key này
            # Thuật toán fallback theo model: mỗi model được retry vài lần trước khi đổi model khác.
            for model_name in models_to_try:#duyet qua danh sach model
                for attempt in range(1, max_attempts_per_model + 1): #duyet qua danh sach model tuc la thu qua 3 lan ko dc qua khác ko dc qua  khac 
                    payload_contents = chat_history + [{"role": "user", "parts": [{"text": prompt}]}]
                    r = await client.post( #goi api gemini
                        f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent",#Truyền api_key qua query param
                        params={"key": api_key}, #tham so truyen vao api gemini
                        json={
                            "contents": payload_contents,
                            "generationConfig": {"temperature": 0.15, "maxOutputTokens": 1024},#nhiep do thap de tra loi chinh xac và gioi han cau tra loi la 1024
                        },
                    )
                    if r.status_code == 200: #neu api tra ve thanh cong
                        data = r.json() #lay du lieu tu api
                        try: #bat loi khi parse du lieu
                            answer_text = "".join(
                                p.get("text", "") #lay text tu api
                                for p in data["candidates"][0]["content"].get("parts", []) #lay parts tu api /parts: content chunks
                                if isinstance(p, dict) #kiem tra xem p co phai la dict khong
                            )
                            return answer_text, model_name, api_key[-4:]
                        except Exception: #neu parse du lieu loi
                            raise HTTPException(status_code=502, detail="Parse error")#tra ve loi parse
                    elif r.status_code == 429:
                        model_quota_count += 1
                        saw_quota_error = True
                        
                    error_msg = r.text #lay thong bao loi
                    last_error = f"{model_name}#attempt{attempt}: {error_msg}"#luu thong bao loi o model nao thu tu nao

                    if r.status_code == 429 or "quota" in error_msg.lower():#neu api tra ve loi quota bat 2 truong hop loi 429 hoac quota
                        saw_quota_error = True #kiem tra xem co loi quota khong
                        model_quota_count += 1
                        break #thoat khoi vong lap attempt, chuyển sang model kế tiếp

                    if r.status_code in (400, 404) and any(
                        k in error_msg.lower() for k in ["model", "not found", "unsupported"]
                    ):#neu api tra ve loi model khong ton tai hoac khong duoc ho tro
                        # Model không hỗ trợ: bỏ qua model này, chuyển model kế tiếp.
                        break #thoat khoi vong lap

                    if r.status_code >= 500 and attempt < max_attempts_per_model:#neu api tra ve loi server tam thoi
                        # Lỗi server tạm thời: retry có backoff trước khi bỏ model.
                        await asyncio.sleep(_backoff_with_jitter(attempt, base_delay=0.6, cap=4.0))#tinh thoi gian delay de tranh request don cum khi retry
                        continue #tiep tuc vong lap

                    break #thoat khoi vong lap
                
                # Nếu request thành công và trả về đáp án, nó đã return ngay ở trên rồi.
                # Nếu chạy xuống đây nghĩa là model này xịt, nó sẽ vòng lên for model_name tiếp theo.
            
            # Nếu thử hết tất cả các model mà model nào cũng bị quota -> account này thật sự cạn quota.
            if model_quota_count >= len(models_to_try):
                _mark_key_cooldown(api_key)

    if saw_quota_error:#neu co loi quota
        raise HTTPException(status_code=429, detail="Quota")#tra ve loi quota

    raise HTTPException(status_code=502, detail=f"Gemini model unavailable: {last_error[:180]}") #tra ve loi model khong kha dung


async def log_to_google(email: str, phone: str, question: str, answer: str): #ham ghi log vao google sheet
    try:
        async with httpx.AsyncClient(timeout=10) as client: #tao client de ghi log vao google sheet
            await client.post(
                GOOGLE_SHEET_API_URL, #url cua google sheet 
                json={
                    "email": email or "N/A",
                    "phone": phone or "N/A",
                    "question": question,
                    "answer": answer,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                },
            )
    except Exception:#neu loi thi bo qua
        pass

#Đoạn _rich_fallback này là phương án dự phòng (fallback) khi Gemini không trả lời được 
#nhưng bạn vẫn muốn trả về câu trả lời có giá trị, đúng ngành thay vì trả lỗi.
def _rich_fallback(question: str, context: List[str], prefix: str) -> str:#ham lay thong tin nganh khi dung ai hoac cau tra loi te hoac ko co cau trl tốt trả về dữ liệu có sẳn
    # Ưu tiên lấy dòng catalog ngành (chắc chắn đúng ngành).
    # Nếu không có ngành, chỉ lấy snippet nếu là lỗi hệ thống, tránh trả lời 'sàu lao'.
    #bullets là chuỗi văn bản đã được format thành dạng danh sách gạch đầu dòng (bullet list) để hiển thị cho dễ đọc.
    major_info = catalog_major(question)#doanh nganh tu cau hoi user trar ve danh sach nganh
    if major_info:#neu co nganh
        bullets = "\n".join(f"- {ln}" for ln in major_info)#tao danh sach nganh them dau - vao moi dong va xuong dong
        
        # Detect what user asked to avoid redundant suggestions
        q_fold = _fold(question)
        suggestions = []
        if "to hop" not in q_fold: suggestions.append("tổ hợp")
        if "chi tieu" not in q_fold: suggestions.append("chỉ tiêu")
        if "hoc phi" not in q_fold: suggestions.append("học phí")
        
        suggest_text = ""
        if suggestions:
            suggest_text = f"Bạn có thể hỏi thêm về {', '.join(suggestions)} của ngành này để mình tư vấn rõ hơn.\n"

        return (
            f"{prefix}\n"
            f"Thông tin ngành này trong danh mục:\n{bullets}\n"
            f"{suggest_text}"
            f"Nguồn: {OFFICIAL_SOURCE_URL}"
        )
    
    # Nếu là lỗi quota/hệ thống, mới lấy snippet để 'chữa cháy'
    if any(k in prefix.lower() for k in ["lỗi", "quá tải", "cooldown"]):#neu la loi quota hoac he thong
        picked = snippets(question, context, 3)#lay snippet tu context
        if picked:#neu co snippet
            bullets = "\n".join(f"- {s}" for s in picked)#tao danh sach snippet
            return f"{prefix}\nTham khảo nhanh dữ liệu hiện có:\n{bullets}\nNguồn: {OFFICIAL_SOURCE_URL}"# bullets o dau da fomat rui

    return (#tra ve cau tra loi
        f"{prefix}\n"#tra ve prefix
        f"Hiện tại dữ liệu tuyển sinh chưa có thông tin cụ thể cho nội dung bạn hỏi.\n"#tra ve loi khuyen
        f"Vui lòng kiểm tra lại tên ngành hoặc xem thêm tại {OFFICIAL_SOURCE_URL}.\n"#tra ve loi khuyen
        f"Nguồn: {OFFICIAL_SOURCE_URL}"#tra ve nguon
    )

#Hàm _expand_if_too_short là bước “hậu xử lý”: nếu câu trả lời từ AI quá ngắn hoặc thiếu chi tiết, 
#nó sẽ tự bổ sung thêm thông tin từ dữ liệu local (context) để câu trả lời đầy đủ hơn.
def _expand_if_too_short(answer: str, question: str, context: List[str]) -> str:
    # Hậu xử lý: nếu AI trả lời quá ngắn thì bơm thêm bullet từ dữ liệu local.
    if len(answer.strip()) >= 180 and answer.count("\n") >= 2:#kiem tra do dai cau tra loi va so dong
        return answer#tra ve cau tra loi
    picked = snippets(question, context, 4)#lay snippet tu context // snippet: đoạn trích ngắn
    if not picked:#neu khong co snippet
        return answer#tra ve cau tra loi
    detail_lines = "\n".join(f"- {s}" for s in picked   )#tao danh sach snippet
    return (
        f"{answer.strip()}\n"#tra ve cau tra loi
        f"Thông tin tham chiếu thêm từ dữ liệu:\n"#tra ve loi khuyen
        f"{detail_lines}\n"#tra ve danh sach snippet
        f"Để mình trả lời sát hơn, bạn có thể hỏi rõ theo tiêu chí: tổ hợp, chỉ tiêu, học phí, phương thức hoặc mốc thời gian.\n"#tra ve loi khuyen
        f"Nguồn: {OFFICIAL_SOURCE_URL}"#tra ve nguon
    )

#dạng câu tra loi 
async def process_chat(question: str, email: str = "", phone: str = "", top_k: int = 8, session_id: str = "") -> Tuple[str, List[str]]:
    raw_question = question
    # Xử lý nhớ ngành học từ câu hỏi trước nếu câu này không nhắc đến
    detected = catalog_major(question)
    if not detected and session_id and session_id in SESSION_MAJOR_MEMORY:
        last_major = SESSION_MAJOR_MEMORY[session_id]
        question = f"Ngành {last_major} - " + question

    # Nếu câu hỏi hiện tại có ngành, lưu lại để ván sau còn nhớ
    if detected and session_id:
        major_line = detected[0]
        parts = major_line.split("|")
        major_name = parts[2].strip() if len(parts) >= 3 else (major_line.split("-")[0].strip() if "-" in major_line else major_line.strip())
        SESSION_MAJOR_MEMORY[session_id] = major_name

    # Retrieval: lấy top-k ngữ cảnh phù hợp nhất từ kho TXT.
    context = find_context(question, top_k)#lay top-k ngu canh phu hop nhat tu kho TXT
    sources = source_names(context, 3)#lay ten nguon tu context

    qf = _fold(question)
    if "to hop" in qf and "xet tuyen" in qf:#kiem tra cau hoi co chua "to hop" va "xet tuyen"
        combo_line = extract_combinations_from_context(context)#lay to hop xet tuyen tu context
        if combo_line:#neu co to hop xet tuyen
            answer = (
                "Theo dữ liệu tuyển sinh hiện có, các tổ hợp xét tuyển là:\n"#tra ve loi khuyen
                f"- {combo_line}\n"#tra ve to hop xet tuyen
                "Nếu bạn muốn, mình có thể tách riêng theo mã tổ hợp (A00, A01, ...) để bạn dễ đối chiếu hơn.\n"#tra ve loi khuyen
                f"Nguồn: {OFFICIAL_SOURCE_URL}"#tra ve nguon
            )
            answer = normalize_source_line(answer)#chuan hoa cau tra loi
            answer = append_video_to_answer(answer, question)#them video vao cau tra loi
            _cache_set(question, answer)#luu cau tra loi vao cache
            await log_to_google(email, phone, question, answer)#ghi log vao google sheet
            return answer, sources#tra ve cau tra loi va nguon

    cached = _cache_get(question)#lay cau tra loi tu cache
    if cached:
        # Cache hit: trả nhanh và vẫn ghi log để theo dõi lịch sử hỏi đáp.
        await log_to_google(email, phone, question, cached)#ghi log vao google sheet
        return cached, sources#tra ve cau tra loi va nguon

    try:
        if _gemini_in_cooldown():#kiem tra gemini co trong cooldown
            # Trong cooldown thì bỏ qua gọi AI, trả fallback local ngay.
            answer = _rich_fallback( #tra ve loi khuyen
                question,
                context,
                "Hệ thống AI đang tạm giới hạn quota, mình trả lời bằng dữ liệu cục bộ trong lúc chờ mở lại.",#tra ve loi khuyen
            )
        else:
            answer_text, model_name, key_suffix = await call_gemini(question, context, chat_history=SESSION_CHAT_HISTORY.get(session_id, []))
            print(f"\n[AI-DEBUG] Session: {session_id} | Model {model_name} | Key ...{key_suffix}")
            
            if "hiện tại mình chưa có dữ liệu về" in answer_text.lower() or len(answer_text) < 20:
                answer = _rich_fallback(question, context, "Tạm thời chưa đủ dữ liệu để kết luận chắc chắn.")
            else:
                answer = _expand_if_too_short(answer_text, question, context)
                
            if session_id:
                if session_id not in SESSION_CHAT_HISTORY:
                    SESSION_CHAT_HISTORY[session_id] = []
                SESSION_CHAT_HISTORY[session_id].append({"role": "user", "parts": [{"text": raw_question}]})
                SESSION_CHAT_HISTORY[session_id].append({"role": "model", "parts": [{"text": answer_text}]})
                # Giữ tối đa 10 lượt (5 hỏi, 5 đáp)
                if len(SESSION_CHAT_HISTORY[session_id]) > 10:
                    SESSION_CHAT_HISTORY[session_id] = SESSION_CHAT_HISTORY[session_id][-10:]
            
    except HTTPException as e:#neu la loi HTTPException
        if e.status_code == 429:
            # Khi quota lỗi, bật cooldown để các request sau không tiếp tục spam Gemini.
            _start_gemini_cooldown()
            answer = _rich_fallback(question, context, "Hệ thống AI đang quá tải, mình chuyển sang trả lời từ dữ liệu cục bộ.")
        else:
            answer = _rich_fallback(question, context, "Đang gặp lỗi hệ thống khi tạo câu trả lời tự động.")
    except Exception:
        answer = _rich_fallback(question, context, "Đang gặp lỗi hệ thống khi xử lý câu hỏi.")

    # Không ép fallback thủ công vào cuối nếu AI trả lại một câu trả lời thực tế, 
    # ngoại trừ các trường hợp AI đã thông báo thiếu dữ liệu từ trước.

    answer = normalize_source_line(answer)#chuan hoa cau tra loi
    answer = append_video_to_answer(answer, question)#them video vao cau tra loi

    _cache_set(question, answer)#luu cau tra loi vao cache
    await log_to_google(email, phone, question, answer)#ghi log vao google sheet
    return answer, sources#tra ve cau tra loi va nguon
