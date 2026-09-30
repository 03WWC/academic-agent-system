"""
Web 层调用 LangGraph 教务多 Agent 系统的聊天服务。
这里保留同步返回和 NDJSON 流式返回两种接口，方便页面和调试脚本复用。
"""

from typing import Any, AsyncGenerator, Callable, Dict, Optional

from langchain_core.messages import AIMessage

from customer_support_chat.app.core.logger import logger
from customer_support_chat.app.graph import multi_agentic_graph


# 操作日志写入器由调用方（如 Web 层）注入。
# 核心层不反向依赖上层模块，避免 core -> web -> core 的循环依赖。
_operation_log_sink: Optional[Callable[[str, Dict[str, Any]], None]] = None


def set_operation_log_sink(
    sink: Optional[Callable[[str, Dict[str, Any]], None]]
) -> None:
    """注册操作日志写入器；传入 None 表示关闭日志记录。"""
    global _operation_log_sink
    _operation_log_sink = sink


ACADEMIC_ASSISTANT_NODES = {
    "primary_assistant",
    "student_profile_assistant",
    "course_policy_assistant",
    "academic_warning_assistant",
    "ticket_assistant",
}


def _to_langgraph_config(session_data: Dict[str, Any]) -> Dict[str, Any]:
    """把 Web 会话配置转换为 LangGraph 需要的 configurable 格式。"""
    return {"configurable": session_data.get("config", {})}


def _add_log(session_id: str, entry: Dict[str, Any]) -> None:
    """写入页面右侧操作日志；未注册写入器时直接跳过。"""
    if _operation_log_sink is not None:
        _operation_log_sink(session_id, entry)


async def process_user_message(session_data: Dict[str, Any], user_message: str) -> str:
    """非流式处理一条用户消息，返回最终 AI 回复。"""
    langgraph_config = _to_langgraph_config(session_data)
    latest_ai_response = ""

    try:
        _add_log(
            session_data["session_id"],
            {"type": "user_input", "title": "用户消息", "content": user_message},
        )

        events = multi_agentic_graph.stream(
            {"messages": [("user", user_message)]},
            langgraph_config,
            stream_mode="values",
        )

        for event in events:
            for message in event.get("messages", []):
                if isinstance(message, AIMessage) and message.content and message.content.strip():
                    latest_ai_response = message.content

        if latest_ai_response:
            _add_log(
                session_data["session_id"],
                {"type": "ai_response", "title": "AI 回复", "content": latest_ai_response},
            )
            return latest_ai_response

        return "抱歉，我没有理解你的问题，可以换一种说法吗？"

    except Exception as e:
        logger.error(f"处理用户消息时出现异常：{e}")
        _add_log(
            session_data["session_id"],
            {"type": "error", "title": "处理错误", "content": str(e)},
        )
        return "处理请求时出现异常，请稍后再试。"


async def stream_user_message(
    session_data: Dict[str, Any], user_message: str
) -> AsyncGenerator[Dict[str, str], None]:
    """以 NDJSON 事件处理用户消息，供 Web 前端逐段展示回复。"""
    langgraph_config = _to_langgraph_config(session_data)
    collected_response: list[str] = []
    seen_tool_runs: set[str] = set()

    try:
        _add_log(
            session_data["session_id"],
            {"type": "user_input", "title": "用户消息", "content": user_message},
        )

        async for event in multi_agentic_graph.astream_events(
            {"messages": [("user", user_message)]},
            langgraph_config,
            version="v2",
        ):
            event_name = event.get("event")
            node_name = event.get("metadata", {}).get("langgraph_node")

            # 只把教务助手节点的自然语言 token 发给前端，避免泄露护栏结构化输出。
            if event_name == "on_chat_model_stream" and node_name in ACADEMIC_ASSISTANT_NODES:
                chunk = event.get("data", {}).get("chunk")
                content = getattr(chunk, "content", "")
                if isinstance(content, str) and content:
                    collected_response.append(content)
                    yield {"type": "token", "content": content}

            elif event_name == "on_tool_start":
                tool_name = event.get("name", "tool")
                tool_input = event.get("data", {}).get("input", {})
                run_id = event.get("run_id", "")
                if run_id and run_id not in seen_tool_runs:
                    seen_tool_runs.add(run_id)
                    content = (
                        "\n".join([f"{k}: {v}" for k, v in tool_input.items()])
                        if isinstance(tool_input, dict)
                        else str(tool_input)
                    )
                    _add_log(
                        session_data["session_id"],
                        {
                            "type": "tool_call",
                            "title": f"{tool_name} 调用",
                            "content": content,
                        },
                    )

            elif event_name == "on_tool_end":
                tool_name = event.get("name", "tool")
                tool_output = event.get("data", {}).get("output", "")
                _add_log(
                    session_data["session_id"],
                    {
                        "type": "tool_result",
                        "title": f"{tool_name} 结果",
                        "content": str(tool_output),
                    },
                )

        final_response = "".join(collected_response).strip()
        if not final_response:
            final_response = "抱歉，我没有理解你的问题，可以换一种说法吗？"
            yield {"type": "token", "content": final_response}

        _add_log(
            session_data["session_id"],
            {"type": "ai_response", "title": "AI 回复", "content": final_response},
        )
        yield {"type": "final", "content": final_response}

    except Exception as e:
        logger.error(f"流式处理用户消息时出现异常：{e}")
        _add_log(
            session_data["session_id"],
            {"type": "error", "title": "流式处理错误", "content": str(e)},
        )
        yield {"type": "error", "content": "处理请求时出现异常，请稍后再试。"}


async def process_user_decision(session_data: Dict[str, Any], decision: str) -> str:
    """教务版暂未启用敏感操作审批，保留接口以兼容 Web 页面。"""
    return "当前教务版没有待审批操作。"
