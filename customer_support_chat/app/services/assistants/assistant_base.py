from typing import Optional
from langchain_core.runnables import Runnable, RunnableConfig
from customer_support_chat.app.core.state import State
from pydantic import BaseModel
from customer_support_chat.app.core.settings import get_settings
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool

settings = get_settings()

# 初始化共享语言模型，供各个 Assistant 复用
llm = ChatOpenAI(
    model=settings.OPENAI_MODEL,
    openai_api_key=settings.OPENAI_API_KEY,
    openai_api_base=settings.OPENAI_BASE_URL if settings.OPENAI_BASE_URL else None,
    temperature=1,
    max_tokens=settings.MAX_TOKENS,  # 限制输出长度，控制调用成本
    extra_body={"thinking": {"type": "disabled"}},
)

class Assistant:
    def __init__(self, runnable: Runnable):
        self.runnable = runnable

    def __call__(self, state: State, config: Optional[RunnableConfig] = None):
        while True:
            result = self.runnable.invoke(state, config)

            if not result.tool_calls and (
                not result.content
                or isinstance(result.content, list)
                and not result.content[0].get("text")
            ):
                messages = state["messages"] + [("user", "请给出真实、可读的中文回复。")]
                state = {**state, "messages": messages}
            else:
                break
        return {"messages": result}

# 定义完成或升级任务的工具
@tool
def CompleteOrEscalate(reason: str) -> str:
    """标记当前任务已完成，或将控制权交还给主 Assistant。
    
    参数：
        reason: 完成任务或升级处理的原因。

    返回：
        确认操作结果的消息。
    """
    return f"任务已完成或已交还主助手。原因：{reason}"
