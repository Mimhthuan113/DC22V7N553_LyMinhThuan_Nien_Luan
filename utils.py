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
    for abbr, full in abbr_map.items():
        if abbr in folded:
            folded = folded.replace(abbr, full)
    return folded

#_fold: ham lam sach text
def _fold(s: str) -> str:#ham lam sach text
    s = unicodedata.normalize("NFD", s)#chuan hoa text
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()#loai bo cac ki tu dac biet va chuyen ve chu thuong

#_keywords: ham trich xuat tu khoa
def _keywords(q: str) -> List[str]:#ham trich xuat tu khoa
    return [w for w in re.findall(r"[0-9A-Za-zÀ-ỹ]+", q.lower()) if len(w) >= 2]#tim cac tu khoa co do dai >=2

#_read_docs: ham doc cac file txt
def _read_docs() -> List[Tuple[str, str]]:#ham doc cac file txt
    if not DATA_DIR.exists():#kiem tra neu DATA_DIR ko ton tai
        return []#tra ve danh sach rong
    docs = []#tao danh sach rong
    for p in sorted(DATA_DIR.glob("*.txt")):#sap xep cac file txt
        try:
            docs.append((p.name, p.read_text(encoding="utf-8", errors="ignore")))#them file txt vao danh sach
        except Exception:#kiem tra loi
            pass#bo qua
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
    return sum(c.count(_fold(k)) for k in keys)#tinh diem cho chunk Với mỗi keyword k Đếm số lần xuất hiện trong chunk Cộng lại tất cả


#_insert_before_source: ham chen text vao truoc nguon
def _insert_before_source(answer: str, line: str) -> str:#ham chen text vao truoc nguon
    m = SOURCE_LINE_RE.search(answer)#tim kiem nguon
    if m:#kiem tra neu tim thay nguon
        return answer[: m.start()].rstrip() + "\n" + line + "\n" + answer[m.start() :].lstrip()#chen text vao truoc nguon
    return answer.rstrip() + "\n" + line#chen text vao cuoi nguon


#catalog_major: Hàm catalog_major của bạn là một bộ “trích xuất + tìm kiếm ngành học” khá thông minh theo kiểu rule-based. 
#Nó lấy ngành từ câu hỏi rồi match với dữ liệu file để tìm dòng phù hợp nhất.
def catalog_major(question: str) -> List[str]:#ham trich xuat nganh
    q = _expand_abbreviations(question)#lam sach cau hoi bo dau tieng viet + mo rong viet tat
    m = re.search(#tìm đoạn sau chữ "nganh" dừng lại khi gặp các stop-word
        r"\bnganh\s+(.+?)(?:\s+co\s+|\s+xet\s+|\s+chi\s+tieu|\s+to\s+hop|\s+hoc\s+phi|\s+yeu\s+cau|\s+diem|\s+ko\b|\s+khong\b|\s+video\b|\s+gioi\s+thieu|\?|$)",#tim kiem nganh
        q,
    )
    if not m:#kiem tra neu tim thay nganh
        return []

    major_phrase = m.group(1).strip()#lay doan sau chu "nganh" va loai bo khoang trang thua
    major_tokens = [#Tách token ngành
        w
        for w in re.findall(r"[a-z0-9]+", major_phrase)#tim cac tu co do dai >=3 va loai bo cac tu "nganh", "chuong", "trinh", "cttt", "ct", "va"
        if len(w) >= 3 and w not in {"nganh", "chuong", "trinh", "cttt", "ct", "va"}
    ]
    if not major_phrase or not major_tokens:#kiem tra neu ko tim thay nganh
        return []

    target = DATA_DIR / "tuyen_sinh_14_danh_muc_to_hop_xet_tuyen.txt"#lay duong dan den file txt
    if not target.exists():#kiem tra neu file txt ko ton tai
        return []

    lines = target.read_text(encoding="utf-8", errors="ignore").splitlines()#doc file txt
    best_lines, best_score = [], 0#best_lines: chua cac dong phu hop nhat, best_score: diem cao nhat
    for i, ln in enumerate(lines):#lap qua cac dong
        if not ln.strip() or len(ln) < 3:#kiem tra neu dong trong hoac do dai nho hon 3
            continue
        folded = _fold(ln)#lam sach dong
        token_hits = sum(1 for w in major_tokens if w in folded)#tinh so tu khoa trong dong
        if token_hits == 0:#kiem tra neu ko tim thay tu khoa
            continue
            #thuật toán chấm điểm (scoring heuristic) diem khi dò từ đúng thì điểmm càng cao
        score = token_hits * 20#tinh diem cho chunk tim cntt thi neu co cntt la 4 token
        if major_phrase in folded:#kiem tra xem chunk co chua nganh ko
            score += 120
        if token_hits >= max(2, len(major_tokens) - 1):#kiem tra xem chunk co chua nhieu tu khoa ko
            score += 30
        if folded.startswith(major_tokens[0]):#kiem tra xem chunk co bat dau bang tu khoa ko
            score += 8

        if score > best_score:#kiem tra neu diem cao nhat
            best_score = score#cap nhat diem cao nhat
            best_lines = [ln]#cap nhat dong phu hop nhat
            # Nếu dòng tiếp theo có mã tổ hợp, lấy luôn
            if i + 1 < len(lines):#kiem tra neu dong tiep theo co ma to hop
                nxt = lines[i + 1].strip()#lay doan tiep theo
                if re.search(r"\b[A-Z][0-9]{2}\b", nxt):#kiem tra neu dong tiep theo co ma to hop
                    best_lines.append(nxt)#them dong tiep theo vao danh sach

    return best_lines if best_score >= 40 else []#tra ve danh sach cac dong phu hop nhat


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
                        return right
                if i + 1 < len(lines):
                    nxt = lines[i + 1].strip(" -;.")
                    if re.search(r"\([A-Z0-9]{2,4}\)", nxt) or re.search(r"\b[A-Z][0-9]{2}\b", nxt):
                        return nxt

            # Một số file ghi trực tiếp dòng tổ hợp không có tiêu đề ngay trước đó.
            if re.search(r"\([A-Z0-9]{2,4}\)", ln) and ";" in ln and "," in ln:
                return ln.strip(" -;.")
    return ""


def major_seed_context(question: str) -> List[str]:
    lines = catalog_major(question)
    if not lines:
        return []
    return [f"[tuyen_sinh_14_danh_muc_to_hop_xet_tuyen.txt] {lines[0]}"]


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
    video_url = pick_major_video(question)
    if not video_url:
        return answer

    line = f"Video giới thiệu ngành: {video_url}"
    if line in answer:
        return answer
    return _insert_before_source(answer, line)
