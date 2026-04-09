# XÂY DỰNG ỨNG DỤNG CHATBOT TƯ VẤN TUYỂN SINH

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Flutter](https://img.shields.io/badge/Flutter-3.x-02569B?style=for-the-badge&logo=flutter&logoColor=white)](https://flutter.dev)
[![Gemini](https://img.shields.io/badge/Gemini%20AI-Pro-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)

**Sinh viên thực hiện:** Lý Minh Thuận · **MSSV:** DC22V7N553  
**Trường:** Đại học Cần Thơ · **Năm học:** 2025 – 2026

</div>

---

## 📖 Giới thiệu

Đây là sản phẩm của đề tài Niên Luận **"Xây dựng ứng dụng Chatbot tư vấn tuyển sinh"** — một hệ thống hỏi đáp thông minh giúp học sinh và phụ huynh tra cứu thông tin tuyển sinh của **Đại học Cần Thơ (CTU)** một cách nhanh chóng và chính xác.

Ứng dụng sử dụng kỹ thuật **RAG (Retrieval-Augmented Generation)**: thay vì để AI "đoán mò", hệ thống trước tiên tra cứu dữ liệu tuyển sinh chính thống, sau đó mới đưa thông tin đó cho Gemini AI tổng hợp câu trả lời. Điều này đảm bảo mọi câu trả lời đều có cơ sở dữ liệu thực tế.

---

## ✨ Tính năng nổi bật

| Tính năng                       | Mô tả                                                                                 |
| ------------------------------- | ------------------------------------------------------------------------------------- |
| 🔍 **Tra cứu thông minh (RAG)** | Tìm đúng thông tin ngành, tổ hợp, chỉ tiêu, học phí và Ký túc xá (KTX) từ kho dữ liệu |
| 🛡️ **Kiểm duyệt tự động**       | Phân loại mượt mà câu hỏi tuyển sinh vs spam; ép AI trả lời bám sát dữ liệu thật      |
| 🤖 **AI Tổng hợp (Gemini)**     | Câu trả lời tự nhiên, thân thiện, kết hợp gọi ý video ngành trực quan                 |
| 🔄 **Xoay vòng API Key**        | Tự động chuyển key khi gặp giới hạn quota, đảm bảo hoạt động liên tục                 |
| 📱 **Đa nền tảng**              | Ứng dụng Flutter chạy trên Web, Android, iOS                                          |
| 📊 **Ghi log Google Sheets**    | Lịch sử hỏi đáp được lưu tự động để cải thiện dữ liệu                                 |
| ⚡ **Cache thông minh**         | Câu hỏi lặp lại được trả lời ngay lập tức, không tốn quota AI                         |

---

## 🏗️ Kiến trúc hệ thống

```
┌─────────────────┐        ┌──────────────────────────────────────┐
│  Flutter App    │  HTTP  │           FastAPI Backend            │
│  (Web/Mobile)   │◄──────►│                                      │
└─────────────────┘        │  ┌────────────┐   ┌───────────────┐  │
                           │  │  Retrieval  │   │  Gemini API   │  │
                           │  │  (data/*.txt)│──►│  (Key Rotate) │  │
                           │  └────────────┘   └───────────────┘  │
                           │         │                             │
                           │         ▼                             │
                           │  ┌───────────────┐                   │
                           │  │ Google Sheets │                   │
                           │  │   (Logging)   │                   │
                           │  └───────────────┘                   │
                           └──────────────────────────────────────┘
```

---

## 📂 Cấu trúc thư mục

```
DC22V7N553_LyMinhThuan_Nien_Luan/
├── 📁 data/                         # Kho dữ liệu tuyển sinh (file .txt)
│   └── tuyen_sinh_*.txt             # Dữ liệu crawl từ tuyensinh.ctu.edu.vn
├── 📁 flutter_chatbot_app/          # Ứng dụng Frontend (Flutter)
│   └── lib/
│       └── services/api_service.dart
├── 🐍 main.py                       # Điểm khởi động FastAPI Server
├── 🐍 ai_service.py                 # Xử lý RAG + gọi Gemini AI
├── 🐍 config.py                     # Quản lý cấu hình từ .env
├── 🐍 utils.py                      # Các hàm tìm kiếm & xử lý văn bản
├── 🐍 scraper.py                    # Công cụ cào dữ liệu từ web tuyển sinh
├── 🐋 docker-compose.yml            # Triển khai bằng Docker
├── 🐋 Dockerfile                    # Cấu hình image Backend
├── ⚙️  nginx.conf                   # Cấu hình Web Server cho Frontend
├── 📄 .env.example                  # File mẫu cấu hình (KHÔNG chứa key thật)
└── 📄 requirements.txt              # Danh sách thư viện Python
```

---

## 🚀 Hướng dẫn cài đặt & Chạy dự án

### ⚡ Cách 1: Dùng Docker (Nhanh nhất — Khuyên dùng)

> **Yêu cầu:** Đã cài [Docker Desktop](https://www.docker.com/products/docker-desktop/)

**Bước 1:** Sao chép file cấu hình và điền API Key của bạn

```bash
# Windows
copy .env.example .env
# Mac/Linux
cp .env.example .env

# Sau đó mở file .env và thay YOUR_KEY vào GEMINI_API_KEY
```

**Bước 2:** Khởi động toàn bộ hệ thống

```bash
docker-compose up --build -d
```

**Bước 3:** Truy cập ứng dụng

- 🌐 **Giao diện Chatbot:** http://localhost:80
- ⚙️ **API Docs (Swagger):** http://localhost:8000/docs
- ❤️ **Kiểm tra sức khỏe:** http://localhost:8000/health

---

### 🛠️ Cách 2: Chạy thủ công (Dành cho phát triển & Debug)

> **Yêu cầu:** Python 3.11+, Flutter SDK

#### Bước 1: Cài đặt thư viện Python

```bash
# Tạo môi trường ảo (khuyến nghị)
python -m venv venv
venv\Scripts\activate       # Windows

# Cài thư viện
pip install -r requirements.txt
```

#### Bước 2: Cấu hình biến môi trường

```bash
# Windows
copy .env.example .env
# Mac/Linux
cp .env.example .env

# Mở file .env và điền GEMINI_API_KEY của bạn vào
```

#### Bước 3: Cập nhật dữ liệu tuyển sinh (tuỳ chọn)

```bash
# Chạy scraper để lấy dữ liệu mới nhất từ tuyensinh.ctu.edu.vn
python scraper.py
```

#### Bước 4: Khởi động Backend

```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

#### Bước 5: Chạy Frontend (Flutter Web)

```bash
cd flutter_chatbot_app
flutter pub get
flutter run -d chrome
```

---

## 🔧 Cấu hình môi trường (`.env`)

Sao chép từ `.env.example` và điền các giá trị cần thiết:

```env
# Bắt buộc: API Key từ Google AI Studio (ai.google.dev)
GEMINI_API_KEY=your_gemini_api_key_here

# Tuỳ chọn: Nhiều key để xoay vòng (tránh lỗi quota)
GEMINI_API_KEYS=key1,key2,key3

# Model AI sử dụng (mặc định: Flash Lite - Nhanh & Miễn phí)
GEMINI_MODEL=models/gemini-2.0-flash-lite

# Thời gian nghỉ khi key bị giới hạn (giây)
GEMINI_KEY_COOLDOWN_SECONDS=900

# URL Google Sheets để ghi log (tuỳ chọn)
GOOGLE_SHEET_API_URL=https://script.google.com/macros/s/.../exec
```

> ⚠️ **Lưu ý bảo mật:** File `.env` đã được thêm vào `.gitignore`. Tuyệt đối không chia sẻ file này lên GitHub.

---

## 🧪 Kiểm thử API

Sau khi chạy server, bạn có thể kiểm thử qua:

**PowerShell:**

```powershell
# Test kiểm tra server
Invoke-RestMethod -Uri "http://localhost:8000/health" -Method GET

# Test câu hỏi về học phí
Invoke-RestMethod -Uri "http://localhost:8000/chat?question=Hoc+phi+nganh+IT" -Method GET

# Test câu hỏi về tổ hợp xét tuyển
Invoke-RestMethod -Uri "http://localhost:8000/chat?question=To+hop+xet+tuyen+nganh+CNTT" -Method GET
```

**Hoặc truy cập Swagger UI tại:** `http://localhost:8000/docs`

---

## 🔄 Cập nhật dữ liệu tuyển sinh

Khi thông tin tuyển sinh CTU thay đổi (ví dụ: đầu mùa tuyển sinh mới):

```bash
# 1. Chạy scraper để crawl dữ liệu mới
python scraper.py

# 2. Restart backend để nạp lại dữ liệu
docker-compose restart backend
# Hoặc nếu chạy thủ công: tắt và chạy lại uvicorn
```

---

## 📊 API Reference

| Method | Endpoint             | Mô tả                                |
| ------ | -------------------- | ------------------------------------ |
| `GET`  | `/health`            | Kiểm tra trạng thái server           |
| `GET`  | `/chat?question=...` | Gửi câu hỏi và nhận trả lời          |
| `POST` | `/chat`              | Gửi câu hỏi (kèm email/phone để log) |

**Request Body (POST /chat):**

```json
{
  "question": "Ngành Công nghệ thông tin có học phí bao nhiêu?",
  "email": "sinhvien@example.com",
  "phone": "0901234567",
  "top_k": 5
}
```

---

## 📄 Giấy phép & Nguồn dữ liệu

- Dự án được phát triển phục vụ mục đích **học tập và nghiên cứu** trong khuôn khổ Niên Luận.
- Dữ liệu tuyển sinh được thu thập từ nguồn chính thức: [tuyensinh.ctu.edu.vn](https://tuyensinh.ctu.edu.vn/)
- © 2026 Lý Minh Thuận — Đại học Cần Thơ
