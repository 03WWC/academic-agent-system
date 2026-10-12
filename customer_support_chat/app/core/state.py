from typing import Annotated, Literal, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import AnyMessage, add_messages

def update_dialog_stack(left: list[str], right: Optional[str]) -> list[str]:
    """压入或弹出对话状态栈。"""
    if right is None:
        return left
    if right == "pop":
        return left[:-1]
    return left + [right]

class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    user_info: str
    # 护栏是否拦下了本轮输入。每次经过 guardrail_check 都会被重新写入，
    # 避免使用 checkpointer 时把上一轮的拦截结果带到下一轮。
    guardrail_blocked: bool
    dialog_state: Annotated[
        list[
            Literal[
                "assistant",
                "student_profile",
                "course_policy",
                "academic_warning",
                "ticket",
            ]
        ],
        update_dialog_stack,
    ]
