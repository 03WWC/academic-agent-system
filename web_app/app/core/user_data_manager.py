import json
import os
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

# 存储用户会话数据的目录
USER_DATA_DIR = "./user_data"

def initialize_user_data_dir():
    """如果用户数据目录不存在，则初始化它。"""
    if not os.path.exists(USER_DATA_DIR):
        os.makedirs(USER_DATA_DIR)

def get_user_data_file(session_id: str) -> str:
    """获取指定用户数据文件路径。"""
    return os.path.join(USER_DATA_DIR, f"{session_id}.json")

def load_user_data(session_id: str) -> Dict[str, Any]:
    """从单独的 JSON 文件加载用户数据。"""
    initialize_user_data_dir()
    user_file = get_user_data_file(session_id)

    if not os.path.exists(user_file):
        return {}

    try:
        # 必须显式指定 UTF-8：否则会按系统默认编码读取，
        # 在中文 Windows 上（GBK）读取 UTF-8 文件会抛 UnicodeDecodeError。
        with open(user_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError, FileNotFoundError):
        return {}

def save_user_data(session_id: str, data: Dict[str, Any]):
    """将用户数据保存到单独的 JSON 文件。"""
    # 写入前确保目录存在：save_user_data 是公开入口，
    # 不应依赖调用方先经过 load_user_data 才把目录建出来。
    initialize_user_data_dir()
    user_file = get_user_data_file(session_id)

    # 先写临时文件、再原子替换。
    # 直接 open(user_file, "w") 会立刻把原文件截断，一旦写入中途失败，
    # 已保存的会话就会变成空文件；而 load_user_data 把无法解析的文件
    # 当作「无数据」返回空字典 —— 用户的历史记录会被静默清空。
    temp_file = f"{user_file}.{uuid.uuid4().hex}.tmp"
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(temp_file, user_file)
    finally:
        # 写入或替换失败时清掉临时文件，不留下垃圾。
        if os.path.exists(temp_file):
            os.remove(temp_file)

def _new_session(session_id: str) -> Dict[str, Any]:
    """构造一个新会话的默认数据结构。"""
    return {
        "session_id": session_id,
        "chat_history": [],
        "pending_action": None,
        "user_decision": None,
        "operation_log": [],
        "created_at": datetime.now().isoformat(),
    }

def _load_or_create(session_id: str) -> Dict[str, Any]:
    """读取已有会话；文件缺失或无法解析时返回新的默认会话（不落盘）。"""
    return load_user_data(session_id) or _new_session(session_id)

def get_user_session(session_id: str) -> Dict[str, Any]:
    """根据会话 ID 获取用户会话；不存在时创建。"""
    user_data = load_user_data(session_id)

    if not user_data:
        user_data = _new_session(session_id)
        save_user_data(session_id, user_data)

    return user_data

def update_user_chat_history(session_id: str, user_message: str, ai_response: str):
    """更新用户会话的聊天历史。"""
    user_data = _load_or_create(session_id)

    # 将新的消息对添加到聊天历史
    user_data["chat_history"].append({
        "timestamp": datetime.now().isoformat(),
        "user_message": user_message,
        "ai_response": ai_response
    })

    save_user_data(session_id, user_data)

def set_pending_action(session_id: str, action_details: Dict[str, Any]):
    """为用户会话设置待处理操作。"""
    user_data = _load_or_create(session_id)

    user_data["pending_action"] = action_details
    save_user_data(session_id, user_data)

def get_pending_action(session_id: str) -> Optional[Dict[str, Any]]:
    """获取用户会话中的待处理操作。"""
    session_data = get_user_session(session_id)
    return session_data.get("pending_action")

def clear_pending_action(session_id: str):
    """清除用户会话中的待处理操作。"""
    # 清除类操作不创建新会话，避免清空动作产生副作用。
    user_data = load_user_data(session_id)
    if user_data:
        user_data["pending_action"] = None
        save_user_data(session_id, user_data)

def set_user_decision(session_id: str, decision: str):
    """为待处理操作设置用户决策。"""
    user_data = _load_or_create(session_id)

    user_data["user_decision"] = decision
    save_user_data(session_id, user_data)

def get_user_decision(session_id: str) -> Optional[str]:
    """获取待处理操作的用户决策。"""
    session_data = get_user_session(session_id)
    return session_data.get("user_decision")

def clear_user_decision(session_id: str):
    """清除待处理操作的用户决策。"""
    user_data = load_user_data(session_id)
    if user_data:
        user_data["user_decision"] = None
        save_user_data(session_id, user_data)

def add_operation_log(session_id: str, log_entry: Dict[str, Any]):
    """向用户会话添加操作日志。"""
    user_data = _load_or_create(session_id)

    # 如果未提供时间戳，则自动添加
    if "timestamp" not in log_entry:
        log_entry["timestamp"] = datetime.now().isoformat()

    user_data["operation_log"].append(log_entry)
    save_user_data(session_id, user_data)

def get_operation_log(session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """获取用户会话的操作日志，可限制条数。"""
    session_data = get_user_session(session_id)
    log = session_data.get("operation_log", [])

    # 按限制返回最近的日志条目
    if limit > 0 and len(log) > limit:
        return log[-limit:]
    return log

def clear_operation_log(session_id: str):
    """清空用户会话的操作日志。"""
    user_data = load_user_data(session_id)
    if user_data:
        user_data["operation_log"] = []
        save_user_data(session_id, user_data)
