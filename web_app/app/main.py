from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from pydantic import BaseModel
import uuid
import os
import sys
import json

# 把项目根目录加入路径，方便 Web 层调用核心 Agent 模块
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from customer_support_chat.app.services.chat_service import process_user_message, stream_user_message
from .core.user_data_manager import (
    get_user_session, 
    update_user_chat_history, 
    get_pending_action, 
    set_user_decision, 
    clear_pending_action, 
    clear_user_decision,
    get_operation_log
)

# 加载 .env 环境变量
load_dotenv()

app = FastAPI()

# 挂载静态资源目录。目录不存在时 StaticFiles 会直接抛 RuntimeError，
# 而 Git 不跟踪空目录，所以这里主动创建一次，保证克隆仓库后也能正常启动。
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 配置 Jinja2 模板目录
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

class ChatMessage(BaseModel):
    message: str

class ApprovalDecision(BaseModel):
    decision: str

def get_session_data(request: Request):
    """获取或创建当前用户的会话数据。"""
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())

    # 读取当前用户的本地会话数据
    session_data = get_user_session(session_id)

    # 确保 LangGraph 运行所需的配置存在
    if "config" not in session_data:
        session_data["config"] = {
            "thread_id": session_id,
            "student_id": "20240001",
        }
    
    return {
        "session_id": session_id,
        "config": session_data["config"],
        "user_data": session_data
    }

@app.get("/", response_class=HTMLResponse)
async def get_chat_page(request: Request, session_data: dict = Depends(get_session_data)):
    """返回聊天页面。"""
    # 写入会话 Cookie，让刷新页面后还能恢复当前会话
    response = templates.TemplateResponse("chat.html", {
        "request": request, 
        "session_id": session_data["session_id"],
        "chat_history": session_data["user_data"].get("chat_history", [])
    })
    response.set_cookie(key="session_id", value=session_data["session_id"])
    return response

@app.post("/chat")
async def chat(chat_message: ChatMessage, session_data: dict = Depends(get_session_data)):
    """处理普通非流式聊天请求，保留给兼容调用。"""
    try:
        # 调用核心 Agent 服务处理用户消息
        ai_response = await process_user_message(session_data, chat_message.message)

        # 保存完整聊天历史
        update_user_chat_history(session_data["session_id"], chat_message.message, ai_response)

        # 返回 Agent 回复
        return JSONResponse(content={"response": ai_response})

    except Exception as e:
        # 服务端打印详细错误，前端只返回友好提示
        print(f"处理聊天消息时出错：{e}")
        return JSONResponse(content={"error": "处理请求时出现异常，请稍后再试。"}, status_code=500)

@app.post("/chat/stream")
async def chat_stream(chat_message: ChatMessage, session_data: dict = Depends(get_session_data)):
    """以 NDJSON 流式返回聊天回复。"""
    async def event_stream():
        final_response = ""

        async for event in stream_user_message(session_data, chat_message.message):
            if event.get("type") == "final":
                final_response = event.get("content", "")
            yield json.dumps(event, ensure_ascii=False) + "\n"

        # 流结束后再写入历史记录，刷新页面也能看到完整对话。
        if final_response:
            update_user_chat_history(
                session_data["session_id"],
                chat_message.message,
                final_response
            )

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")

# 人在回路审批接口

@app.get("/pending-action")
async def get_pending_action_endpoint(session_data: dict = Depends(get_session_data)):
    """检查当前会话是否存在待审批操作。"""
    try:
        pending_action = get_pending_action(session_data["session_id"])
        if pending_action:
            return JSONResponse(content={"pending_action": pending_action})
        else:
            return JSONResponse(content={"pending_action": None})
    except Exception as e:
        print(f"检查待审批操作时出错：{e}")
        return JSONResponse(content={"error": "处理请求时出现异常，请稍后再试。"}, status_code=500)


@app.post("/approve-action")
async def approve_action(request: Request, session_data: dict = Depends(get_session_data)):
    """批准当前待审批操作。"""
    try:
        # 调用核心服务处理用户批准结果
        from customer_support_chat.app.services.chat_service import process_user_decision
        ai_response = await process_user_decision(session_data, "approve")

        # 把审批动作写入聊天历史
        update_user_chat_history(session_data["session_id"], "[用户批准操作]", ai_response)

        # 返回审批后的处理结果
        return JSONResponse(content={"response": ai_response})

    except Exception as e:
        # 服务端打印详细错误，前端只返回友好提示
        print(f"处理审批通过操作时出错：{e}")
        return JSONResponse(content={"error": "处理请求时出现异常，请稍后再试。"}, status_code=500)


@app.post("/reject-action")
async def reject_action(request: Request, session_data: dict = Depends(get_session_data)):
    """拒绝当前待审批操作。"""
    try:
        # 调用核心服务处理用户拒绝结果
        from customer_support_chat.app.services.chat_service import process_user_decision
        ai_response = await process_user_decision(session_data, "reject")

        # 把拒绝动作写入聊天历史
        update_user_chat_history(session_data["session_id"], "[用户拒绝操作]", ai_response)

        # 返回拒绝后的处理结果
        return JSONResponse(content={"response": ai_response})

    except Exception as e:
        # 服务端打印详细错误，前端只返回友好提示
        print(f"处理审批拒绝操作时出错：{e}")
        return JSONResponse(content={"error": "处理请求时出现异常，请稍后再试。"}, status_code=500)

@app.get("/operation-log")
async def get_operation_log_endpoint(session_data: dict = Depends(get_session_data)):
    """获取当前会话的操作日志。"""
    try:
        # 只返回最近 20 条，避免页面轮询时传输过多数据
        operation_log = get_operation_log(session_data["session_id"], limit=20)
        return JSONResponse(content={"operation_log": operation_log})
    except Exception as e:
        print(f"获取操作日志时出错：{e}")
        return JSONResponse(content={"error": "处理请求时出现异常，请稍后再试。"}, status_code=500)
