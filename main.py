from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ai_service import process_chat
from config import OFFICIAL_SOURCE_URL


class ChatRequest(BaseModel):#định nghĩa cấu trúc dữ liệu câu hỏi gửi lên từ người dùng
    question: str = Field(..., min_length=1)#câu hỏi
    email: str = ""#email
    phone: str = ""#số điện thoại
    top_k: int = Field(5, ge=1, le=20)#số lượng ngữ cảnh


class ChatResponse(BaseModel):#đóng gói câu trả lời và các nguồn dữ liệu liên quan
    answer: str#câu trả lời
    context_used: List[str]#nguồn dữ liệu
    more_info_url: str = OFFICIAL_SOURCE_URL#url nguồn


# TÁC DỤNG: Khởi tạo Server FastAPI và cấu hình CORS (Bảo mật truy cập).
# LUỒNG ĐI: Cho phép các ứng dụng Frontend (Flutter/Vue) kết nối an toàn tới API.
app = FastAPI()#khởi tạo server FastAPI
app.add_middleware(#cấu hình CORS (Bảo mật truy cập)
    CORSMiddleware,
    allow_origins=["*"],#cho phép tất cả các nguồn
    allow_credentials=False,#không cho phép truy cập
    allow_methods=["*"],#cho phép tất cả các phương thức
    allow_headers=["*"],#cho phép tất cả các header
)


@app.get("/health")#kiểm tra trạng thái của server
def health():#trả về trạng thái ok
    return {"status": "ok"}#trả về trạng thái ok


@app.get("/chat")#lấy câu trả lời từ AI
async def chat_get(question: str, email: str = "", phone: str = "", top_k: int = 5):#lấy câu trả lời từ AI 
    answer, sources = await process_chat(question=question, email=email, phone=phone, top_k=top_k)#lấy câu trả lời từ AI
    return ChatResponse(answer=answer, context_used=sources)#trả về câu trả lời và nguồn


@app.post("/chat")#lấy câu trả lời từ AI
async def chat_post(req: ChatRequest) -> ChatResponse:#lấy câu trả lời từ AI 
    answer, sources = await process_chat(#lấy câu trả lời từ AI 
        question=req.question,#câu hỏi
        email=req.email,#email
        phone=req.phone,#số điện thoại
        top_k=req.top_k,#số lượng ngữ cảnh
    )
    return ChatResponse(answer=answer, context_used=sources)#trả về câu trả lời và nguồn


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
