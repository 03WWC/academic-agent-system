from typing import Optional
from langchain_core.runnables import Runnable, RunnableConfig
from customer_support_chat.app.core.state import State
from pydantic import BaseModel
from customer_support_chat.app.core.settings import PLACEHOLDER_API_KEY, get_settings
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool

settings = get_settings()

# 初始化共享语言模型，供各个 Assistant 复用
llm = ChatOpenAI(
    model=settings.OPENAI_MODEL,
    openai_api_key=settings.OPENAI_API_KEY or PLACEHOLDER_API_KEY,
    openai_api_base=settings.OPENAI_BASE_URL if settings.OPENAI_BASE_URL else None,
    temperature=1,
    max_tokens=settings.MAX_TOKENS,  # 限制输出长度，控制调用成本
    extra_body={"thinking": {"type": "disabled"}},
)

def _is_empty_reply(result) -> bool:
    """判断模型回复是否既没有工具调用、也没有可读文本。"""
    if result.tool_calls:
        return False

    content = result.content
    if not content:
        return True

    if isinstance(content, list):
        first = content[0] if content else None
        return not (isinstance(first, dict) and first.get("text"))

    return False


class Assistant:
    # 一次正常询问 + 最多再补问两次。
    # 原实现是 while True 且没有计数器：模型持续返回空内容时会无限循环，
    # 请求永不返回、工作线程被占死，而且每一次循环都是一次真实的大模型调用。
    MAX_ATTEMPTS = 3

    def __init__(self, runnable: Runnable):
        self.runnable = runnable

    def __call__(self, state: State, config: Optional[RunnableConfig] = None):
        result = None

        for _ in range(self.MAX_ATTEMPTS):
            result = self.runnable.invoke(state, config)

            if not _is_empty_reply(result):
                break

            messages = state["messages"] + [("user", "请给出真实、可读的中文回复。")]
            state = {**state, "messages": messages}

        # 连续多次空回复时直接返回最后一次结果，不再继续追问。
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
