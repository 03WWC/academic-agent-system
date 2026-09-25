from typing import Callable

from langchain_core.messages import ToolMessage

from customer_support_chat.app.core.state import State


def create_entry_node(assistant_name: str, new_dialog_state: str) -> Callable:
    """创建专业助手入口节点，把主助手的委派意图转成工具响应消息。"""

    def entry_node(state: State) -> dict:
        last_message = state["messages"][-1]
        tool_messages = []

        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            for tool_call in last_message.tool_calls:
                tool_messages.append(
                    ToolMessage(
                        content=(
                            f"当前助手已切换为 {assistant_name}。请回顾上方主助手与用户之间的对话。"
                            f"用户意图尚未满足。请使用可用工具帮助用户。记住，你现在是 {assistant_name}。"
                            "只有成功调用对应工具后，查询、分析或工单处理才算完成。"
                            "如果用户改变主意，或需要处理其他任务，请调用 CompleteOrEscalate 函数，让主助手重新接管。"
                            "不要说明你是谁，只需要作为该专业助手的代理继续处理。"
                        ),
                        tool_call_id=tool_call["id"],
                    )
                )
        else:
            # 正常委派流程中不应进入该分支；保留兜底，便于调试图状态。
            tool_messages.append(
                ToolMessage(
                    content=(
                        f"当前助手已切换为 {assistant_name}。请根据已有对话继续完成教务服务任务。"
                    ),
                    tool_call_id="fallback_tool_call_id",
                )
            )

        return {
            "messages": tool_messages,
            "dialog_state": new_dialog_state,
        }

    return entry_node


def handle_tool_error(state) -> dict:
    """把工具异常转换为 ToolMessage，避免模型侧 tool_call 响应链断裂。"""
    error = state.get("error")
    tool_calls = state["messages"][-1].tool_calls
    return {
        "messages": [
            {
                "type": "tool",
                "content": f"工具调用出错：{repr(error)}\n请修正工具参数后再试。",
                "tool_call_id": tc["id"],
            }
            for tc in tool_calls
        ]
    }


def create_tool_node_with_fallback(tools: list):
    """创建带异常兜底的 LangGraph ToolNode。"""
    from langchain_core.runnables import RunnableLambda
    from langgraph.prebuilt import ToolNode

    return ToolNode(tools).with_fallbacks(
        [RunnableLambda(handle_tool_error)], exception_key="error"
    )
