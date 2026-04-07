import json
import re
import time
import unicodedata
from typing import Dict, List, Tuple

from config import DATA_DIR, OFFICIAL_SOURCE_URL

VIDEO_INDEX_CACHE = {"loaded_at": 0.0, "items": []}#Luu tru video nganh Tránh gọi API / đọc file nhiều lần
SOURCE_LINE_RE = re.compile(r"(?im)^\s*Nguồn\s*:\s*.*$")#nguon 
DOC_PREFIX_RE = re.compile(r"^\[[^\]]+\]\s*")
SNIPPET_NOISE = {#cac tu/phrase rác thường gặp trên web (menu, button, navbar).
    "trang chu",
    "tin moi:",
    "danh muc",
    "tim kiem",
    "xem them",
    "lien he",
    "thong bao",
    "phu luc",
}

# Cache bảng viết tắt load từ file JSON (chỉ đọc 1 lần khi khởi động)
_ABBR_CACHE: Dict[str, str] = {}
_MAJOR_NAMES_CACHE: List[Tuple[str, str]] = []

def _load_major_names() -> List[Tuple[str, str]]:
    global _MAJOR_NAMES_CACHE
    if _MAJOR_NAMES_CACHE:
        return _MAJOR_NAMES_CACHE
        
    target = DATA_DIR / "tuyen_sinh_14_danh_muc_to_hop_xet_tuyen.txt"
    if not target.exists():
        return []
        
    lines = target.read_text(encoding="utf-8", errors="ignore").splitlines()
    for ln in lines:
        if "|" in ln:
            parts = ln.split("|")
            if len(parts) >= 3:
                name = parts[2].strip()
                _MAJOR_NAMES_CACHE.append((name, _fold(name)))
    
    # Sắp xếp tên từ dài đến ngắn để ưu tiên match cụm dài (vd: Kỹ thuật phần mềm > phần mềm)
    _MAJOR_NAMES_CACHE.sort(key=lambda x: len(x[1]), reverse=True)
    return _MAJOR_NAMES_CACHE


def _load_abbreviations() -> Dict[str, str]:
    """Đọc bảng viết tắt từ data/abbreviations.json, gộp tất cả nhóm thành 1 dict phẳng."""
    global _ABBR_CACHE
    if _ABBR_CACHE:
        return _ABBR_CACHE

    abbr_path = DATA_DIR / "abbreviations.json"
    if not abbr_path.exists():
        return {}

    try:
        raw = json.loads(abbr_path.read_text(encoding="utf-8", errors="ignore"))
        merged: Dict[str, str] = {}
        for key, value in raw.items():
            if key.startswith("_"):  # bỏ qua _metadata
                continue
            if isinstance(value, dict):  # nhóm con (nganh_hoc, teencode...)
                merged.update(value)
            elif isinstance(value, str):  # dòng đơn lẻ
                merged[key] = value
        _ABBR_CACHE = merged
        print(f"[abbr] Đã load {len(merged)} viết tắt từ abbreviations.json")
        return merged
    except Exception as e:
        print(f"[abbr] Lỗi đọc abbreviations.json: {e}")
        return {}


def _expand_abbreviations(text: str) -> str:
    """Mở rộng viết tắt phổ biến trong câu hỏi để tăng khả năng tìm kiếm."""
    abbr_map = _load_abbreviations()
    folded = _fold(text)
    # Sắp xếp key theo độ dài giảm dần để ưu tiên các cụm từ dài trước (VD: 'cntt' trước 'ct')
    sorted_abbrs = sorted(abbr_map.keys(), key=len, reverse=True)
    for abbr in sorted_abbrs:
        full = abbr_map[abbr]
        # Chỉ thay thế khi khớp nguyên từ (whole word)
        pattern = re.compile(rf"\b{re.escape(abbr)}\b")
        folded = pattern.sub(full, folded)
    return folded

#_fold: ham lam sach text
def _fold(s: str) -> str:#ham lam sach text
    s = unicodedata.normalize("NFD", s)#chuan hoa text
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()#loai bo cac ki tu dac biet va chuyen ve chu thuong

#_keywords: ham trich xuat tu khoa
def _keywords(q: str) -> List[str]:#ham trich xuat tu khoa
    words = [w for w in re.findall(r"[0-9A-Za-zÀ-ỹ]+", q.lower()) if len(w) >= 2]
    # Loại bỏ các stopword không mang ý nghĩa tìm kiếm
    stop_words = {"dạ", "cho", "em", "hỏi", "năm", "học", "mấy", "ạ", "nay", "sao", "có", "không", "thì", "là", "gì", "bao", "nhiêu", "ngành"}
    return [w for w in words if w not in stop_words]

#_read_docs: ham doc cac file txt
def _read_docs() -> List[Tuple[str, str]]:#ham doc cac file txt
    if not DATA_DIR.exists():#kiem tra neu DATA_DIR ko ton tai
        return []#tra ve danh sach rong
    docs = []#tao danh sach rong
    for p in sorted(DATA_DIR.glob("*.txt")):#sap xep cac file txt
        if p.name == "tuyen_sinh_2026.txt":
            continue
        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
            # Tối ưu file danh mục bằng trích xuất header và bảng, gỡ dòng 12.000
            if p.name == "tuyen_sinh_14_danh_muc_to_hop_xet_tuyen.txt":
                filtered_lines = []
                for ln in content.splitlines():
                    if "Tổng chỉ tiêu:" in ln or "12.000" in ln:
                        continue
                    filtered_lines.append(ln)
                content = "\n".join(filtered_lines)
                
            docs.append((p.name, content))
        except Exception:
            pass
    return docs

#_chunks: ham chia text thanh cac chunk
def _chunks(text: str, max_chars: int = 800) -> List[str]:#ham chia text thanh cac chunk do dai moi chunk la 800 ki tu
    parts = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]#tach text thanh cac chunk 1 hoặc nhiều dòng trống → dùng để tách đoạn ["Đoạn 1", "Đoạn 2", "Đoạn 3"]
    chunks = []#tao danh sach rong
    for p in parts:
        if len(p) <= max_chars:#kiem tra neu do dai chunk nho hon 800
            chunks.append(p)#them chunk vao danh sach
        else:
            for i in range(0, len(p), max_chars):#lap lai khi do dai chunk lon hon 800
                chunks.append(p[i : i + max_chars].strip())#them chunk vao danh sach
    return [c for c in chunks if c]#tra ve danh sach cac chunk


#_score: ham tinh diem cho chunk
def _score(chunk: str, keys: List[str]) -> int:#ham tinh diem cho chunk
    c = _fold(chunk)#lam sach chunk bo giau tieng viet vs dac biet ra
    score = 0
    for k in keys:
        kf = _fold(k)
        score += len(re.findall(rf"\b{re.escape(kf)}\b", c))
    return score


#_insert_before_source: ham chen text vao truoc nguon
def _insert_before_source(answer: str, line: str) -> str:#ham chen text vao truoc nguon
    m = SOURCE_LINE_RE.search(answer)#tim kiem nguon
    if m:#kiem tra neu tim thay nguon
        return answer[: m.start()].rstrip() + "\n" + line + "\n" + answer[m.start() :].lstrip()#chen text vao truoc nguon
    return answer.rstrip() + "\n" + line#chen text vao cuoi nguon


#catalog_major: Hàm catalog_major của bạn là một bộ “trích xuất + tìm kiếm ngành học” khá thông minh theo kiểu rule-based. 
#Nó lấy ngành từ câu hỏi rồi match với dữ liệu file để tìm dòng phù hợp nhất.
def catalog_major(question: str) -> List[str]:
    q = _expand_abbreviations(question)
    q_fold = _fold(q)
    
    major_phrase = ""
    major_tokens = []
    
    # 1. Thử dò trực tiếp từ danh mục ngành trước (Chính xác cao)
    for name, folded_name in _load_major_names():
        if len(folded_name) >= 4 or folded_name == "y":
            pattern = re.compile(rf"(?<![a-z]){re.escape(folded_name)}(?![a-z])")
            if pattern.search(q_fold):
                major_phrase = folded_name
                major_tokens = folded_name.split()
                break

    # 2. Nếu không có trong danh sách chuẩn, fallback về regex heurictics
    if not major_phrase:
        m = re.search(r"nganh\s+([^,.;?ạ!]+)", q)
        MAJOR_EXCLUDES = {
            "a", "nhe", "di", "nhi", "oi", "da", "nha", "ha", "voi", "ve", "no", "muon", "hoc", "em", "cho", "xin", 
            "tinh", "hinh", "la", "may", "nam", "bao", "nhieu", "sao", "thi", "gi", "nao", "co", "khong",
            "nay", "nhiu", "vay", "truong", "he", "dao", "tao", "diem", "chuan", "thong", "tin", "chi", "tieu", "muc", "v", "vong", "cua", "khoang", "khoi", "xet", "tuyen", "to", "hop"
        }
        if m:
            raw_phrase = m.group(1).strip()
            words = raw_phrase.split()
            filtered_words = [w for w in words if w not in MAJOR_EXCLUDES]
            major_phrase = " ".join(filtered_words)
            major_tokens = [w for w in filtered_words if len(w) >= 2 or w.lower() == "y"]

    if not major_phrase or not major_tokens:
        return []

    target = DATA_DIR / "tuyen_sinh_14_danh_muc_to_hop_xet_tuyen.txt"
    if not target.exists():
        return []

    lines = target.read_text(encoding="utf-8", errors="ignore").splitlines()
    best_lines, best_score = [], 0
    
    token_patterns = [re.compile(rf"\b{re.escape(w)}\b") for w in major_tokens]
    
    for i, ln in enumerate(lines):
        if not ln.strip() or len(ln) < 3:
            continue
        folded = _fold(ln)
        
        token_hits = sum(1 for p in token_patterns if p.search(folded))
        if token_hits == 0:
            continue
            
        score = token_hits * 30
        if major_phrase in folded:
            score += 150
            if len(folded.split()) <= len(major_tokens) + 2:
                score += 100
                
        if token_hits >= len(major_tokens):
            score += 50

        if score > best_score:
            best_score = score
            best_lines = [ln.strip(" -;")]
            if i + 1 < len(lines):
                nxt = lines[i + 1].strip()
                if re.search(r"\((?:[A-Z0-9]{2,4}|[A-Z][0-9]{2})\)", nxt) or re.search(r"\b[A-Z][0-9]{2}\b", nxt):
                    best_lines.append(nxt)

    return best_lines if best_score >= 70 else []


def snippets(question: str, context: List[str], max_items: int = 3) -> List[str]:
    keys = _keywords(question)

    out = []
    for chunk in context:
        body = DOC_PREFIX_RE.sub("", chunk.strip())
        lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
        picked = []
        for ln in lines:
            folded_ln = _fold(ln)
            if len(ln) < 12 or folded_ln in SNIPPET_NOISE or ln.startswith(("===", "---", "***")):
                continue
            # Nếu có nhiều từ khóa, yêu cầu khớp ít nhất 2 từ hoặc 50% số từ khóa để tăng độ liên quan
            hits = sum(1 for k in keys if k in folded_ln)
            if keys and hits < min(2, len(keys)):
                continue
            picked.append(ln)
            if len(picked) >= 6:
                break
        if picked and sum(len(p) for p in picked) >= 25:
            out.append(" ".join(picked)[:550])
        if len(out) >= max_items:
            break
    return out


def extract_combinations_from_context(context: List[str]) -> str:
    # Ưu tiên lấy đúng dòng tổ hợp từ TXT để tránh AI suy diễn thêm môn.
    for chunk in context:
        body = DOC_PREFIX_RE.sub("", chunk.strip())
        lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
        for i, ln in enumerate(lines):
            f = _fold(ln)
            if "to hop xet tuyen" in f:
                if ":" in ln:
                    right = ln.split(":", 1)[1].strip(" -;.")
                    if right and len(right) >= 8:
                        return right.replace('+', '').strip()
                if i + 1 < len(lines):
                    nxt = lines[i + 1].strip(" -;.")
                    if re.search(r"\([A-Z0-9]{2,4}\)", nxt) or re.search(r"\b[A-Z][0-9]{2}\b", nxt):
                        return nxt.replace('+', '').strip()

            # Một số file ghi trực tiếp dòng tổ hợp không có tiêu đề ngay trước đó.
            if re.search(r"\([A-Z0-9]{2,4}\)", ln) and ";" in ln and "," in ln:
                return ln.strip(" -;.").replace('+', '').strip()
    return ""


def major_seed_context(question: str) -> List[str]:
    lines = catalog_major(question)
    if not lines:
        return []
    
    seed = [f"[tuyen_sinh_14_danh_muc_to_hop_xet_tuyen.txt] Thông tin (STT | Mã ngành | Tên ngành | Chỉ tiêu | Tổ hợp): {lines[0]}"]
    
    # Tự động tìm file chi tiết ngành (VD: tuyen_sinh_127_thu_y.txt)
    # Dữ liệu bảng: "97 | 7340115 | Marketing | 100 | A00, A01, C02, D01"
    if "|" in lines[0]:
        parts = lines[0].split("|")
        major_name = parts[2].strip() if len(parts) >= 3 else lines[0].strip()
    else:
        major_name = lines[0].strip()
        
    major_slug = _fold(major_name).replace(" ", "_")
    
    # Rút gọn token để match tên file (VD: công nghệ thông tin -> file là cntt)
    tokens = [w for w in _fold(major_name).split() if w]
    
    for p in DATA_DIR.glob("*.txt"):
        if p.name == "tuyen_sinh_2026.txt" or p.name == "tuyen_sinh_14_danh_muc_to_hop_xet_tuyen.txt":
            continue
        p_fold = _fold(p.name)
        # Match theo slug hoặc có chứa tối thiểu 2 tokens (tránh nhầm lẫn quá xa)
        if major_slug in p_fold or (len(tokens) >= 2 and sum(1 for t in tokens if t in p_fold) >= min(2, len(tokens))):
            try:
                content = p.read_text(encoding="utf-8", errors="ignore")
                # Nạp 1500 ký tự quan trọng nhất của file ngành
                seed.append(f"[{p.name}] {content[:1500]}")
                break
            except:
                pass
    return seed


def source_names(context: List[str], max_items: int = 3) -> List[str]:
    out: List[str] = []
    for c in context:
        m = re.match(r"\[([^\]]+)\]", c.strip())
        if m:
            out.append(m.group(1))
            if len(out) >= max_items:
                break
    return out


def find_context(question: str, top_k: int = 5) -> List[str]:
    docs = _read_docs()
    if not docs:
        return []

    expanded_q = _expand_abbreviations(question)#mo rong viet tat truoc khi tim kiem
    keys = _keywords(expanded_q)
    if not keys:
        out = []
        for fname, content in docs:
            for chunk in _chunks(content):
                out.append(f"[{fname}] {chunk}")
                if len(out) >= top_k:
                    return out
        return out

    candidates = []
    for fname, content in docs:
        for chunk in _chunks(content):
            s = _score(chunk, keys)
            if s > 0:
                candidates.append((s, f"[{fname}] {chunk}"))

    candidates.sort(reverse=True)
    ranked = [c[1] for c in candidates[:top_k]]

    seed = major_seed_context(question)
    
    # 🎯 FIX CỨNG: Nếu câu hỏi có nhắc KTX thì ưu tiên đẩy file KTX vào ngay đầu
    q_lower = expanded_q.lower()
    if "ktx" in q_lower or "ky tuc xa" in q_lower:
        ktx_file = DATA_DIR / "tuyen_sinh_150_ktx.txt"
        if ktx_file.exists():
            ktx_content = ktx_file.read_text(encoding="utf-8", errors="ignore")
            # Trích phần giới thiệu trọng tâm
            seed = [f"[tuyen_sinh_150_ktx.txt] {ktx_content[:1500]}"] + seed

    if seed:
        existing = set(ranked)
        for s in seed:
            if s not in existing:
                ranked = [s] + ranked
        ranked = ranked[:top_k]
    return ranked


def normalize_source_line(answer: str) -> str:
    cleaned = answer
    cleaned = re.sub(r"(?is)nguồn\s*:\s*https?://\S+", f"Nguồn: {OFFICIAL_SOURCE_URL}", cleaned)
    cleaned = re.sub(r"(?im)^\s*nguồn\s*:\s*.*$", f"Nguồn: {OFFICIAL_SOURCE_URL}", cleaned)

    lines = [ln.rstrip() for ln in cleaned.splitlines()]
    src_lines = [i for i, ln in enumerate(lines) if SOURCE_LINE_RE.match(ln)]
    if src_lines:
        first = src_lines[0]
        lines[first] = f"Nguồn: {OFFICIAL_SOURCE_URL}"
        for idx in reversed(src_lines[1:]):
            lines.pop(idx)
        cleaned = "\n".join(lines).strip()
    else:
        cleaned = ("\n".join(lines).strip() + f"\nNguồn: {OFFICIAL_SOURCE_URL}").strip()
    return cleaned


def _set_video_cache(items: List[dict]) -> List[dict]:
    VIDEO_INDEX_CACHE["loaded_at"] = time.time()
    VIDEO_INDEX_CACHE["items"] = items
    return items


def load_video_index() -> List[dict]:
    if VIDEO_INDEX_CACHE["items"] and (time.time() - VIDEO_INDEX_CACHE["loaded_at"]) < 300:
        return VIDEO_INDEX_CACHE["items"]

    idx_path = DATA_DIR / "nganh_video_index.json"
    if not idx_path.exists():
        return _set_video_cache([])

    try:
        data = json.loads(idx_path.read_text(encoding="utf-8", errors="ignore"))
        items = data.get("items", []) if isinstance(data, dict) else []
        return _set_video_cache(items if isinstance(items, list) else [])
    except Exception:
        return _set_video_cache([])


def pick_major_video(question: str) -> str:
    q = _expand_abbreviations(question)#mo rong viet tat truoc khi tim video
    m = re.search(
        r"\bnganh\s+(.+?)(?:\s+co\s+|\s+xet\s+|\s+chi\s+tieu|\s+to\s+hop|\s+hoc\s+phi|\s+yeu\s+cau|\s+diem|\s+ko\b|\s+khong\b|\s+video\b|\s+gioi\s+thieu|\?|$)",
        q,
    )
    if not m:
        return ""

    major_phrase = m.group(1).strip()
    major_tokens = [
        w
        for w in re.findall(r"[a-z0-9]+", major_phrase)
        if len(w) >= 3 and w not in {
            "nganh", "chuong", "trinh", "cttt", "ct", "va", "hoc", "phi", "cho", "biet", "nhung", "nao", "co", "khong"
        }
    ]
    if not major_phrase or not major_tokens:
        return ""

    items = load_video_index()
    if not items:
        return ""

    best_score = 0
    best_url = ""
    for item in items:
        if not isinstance(item, dict):
            continue
        video_url = (item.get("video_url") or "").strip()
        title = _fold(item.get("title") or "")
        detail = _fold(item.get("detail_url") or "")
        if not video_url:
            continue

        token_hits = sum(1 for t in major_tokens if t in title or t in detail)
        if token_hits == 0:
            continue

        score = token_hits * 20
        if _fold(major_phrase) in title:
            score += 100
        if "/video_nganh/" in video_url.lower():
            score += 30

        if score > best_score:
            best_score = score
            best_url = video_url

    return best_url if best_score >= 60 else ""


def append_video_to_answer(answer: str, question: str) -> str:
    # Nếu câu hỏi mục tiêu vào dữ liệu cụ thể, hạn chế nhồi video gây loãng
    q_fold = _fold(question)
    skip_keywords = ["chi tieu", "hoc phi", "to hop", "diem chuan", "xet tuyen", "bao nhieu", "bao nhiu", "muc luong", "khoi"]
    override_keywords = ["video", "gioi thieu", "chi tiet", "thong tin", "tong quan"]
    
    if any(k in q_fold for k in skip_keywords) and not any(o in q_fold for o in override_keywords):
        return answer

    video_url = pick_major_video(question)
    if not video_url:
        return answer

    line = f"Em có thể tham khảo thêm video giới thiệu về ngành tại đây: {video_url}"
    if line in answer:
        return answer
    return _insert_before_source(answer, line)
