import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

APP_DIR = Path(__file__).parent
DATA_DIR = APP_DIR / "data"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_API_KEYS = [
    k.strip()
    for k in os.getenv("GEMINI_API_KEYS", "").split(",")
    if k.strip()
]
if not GEMINI_API_KEYS and GEMINI_API_KEY:
    GEMINI_API_KEYS = [GEMINI_API_KEY]
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "models/gemini-2.5-flash-lite").strip()
GEMINI_FALLBACK_MODELS = [
    m.strip()
    for m in os.getenv(
        "GEMINI_FALLBACK_MODELS",
        "models/gemini-1.5-flash-lite,models/gemini-2.5-flash",
    ).split(",")
    if m.strip()
]

GOOGLE_SHEET_API_URL = os.getenv(
    "GOOGLE_SHEET_API_URL",
    "https://script.google.com/macros/s/AKfycbwO3lPgTYlGbPOMVh8VPTcNp3158Tz54Tgmnrbh8_J1fze-wrHtdBcRfhTXuxX_QL2ZCQ/exec",
).strip()
OFFICIAL_SOURCE_URL = os.getenv(
    "OFFICIAL_SOURCE_URL", "https://tuyensinh.ctu.edu.vn/"
).strip()

GEMINI_COOLDOWN_SECONDS = int(os.getenv("GEMINI_COOLDOWN_SECONDS", "300"))
GEMINI_KEY_COOLDOWN_SECONDS = int(os.getenv("GEMINI_KEY_COOLDOWN_SECONDS", "900"))
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "1800"))

PROMPT = """Bạn là tư vấn viên tuyển sinh Đại học Cần Thơ.
Yêu cầu trả lời:
- Trả lời tiếng Việt tự nhiên, thân thiện, ngắn gọn, súc tích (phù hợp xem trên di động).
- Ưu tiên trả lời đúng trọng tâm câu hỏi ngay lập tức.
- Sử dụng danh sách (bullet points) khi liệt kê dữ liệu (tổ hợp, chỉ tiêu, ngành...) để dễ theo dõi.
- Độ dài: tối đa 3-5 câu hoặc 1 đoạn ngắn, tránh lặp ý và tránh giải thích lan man.
- Chỉ dùng thông tin có trong dữ liệu cung cấp, không suy diễn linh tinh.
- Nếu không có thông tin chính xác về một ngành cụ thể (ngành không tồn tại), hãy nói rõ là chưa có dữ liệu cho ngành đó thay vì trả lời chung chung về các ngành khác.
- Kết thúc bằng dòng: \"Nguồn: https://tuyensinh.ctu.edu.vn/\".
"""
