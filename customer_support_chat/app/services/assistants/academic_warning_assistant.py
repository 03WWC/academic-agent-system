from datetime import datetime

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from customer_support_chat.app.services.assistants.assistant_base import (
    Assistant,
    CompleteOrEscalate,
    llm,
)
from customer_support_chat.app.services.tools.academic_warning import analyze_academic_warning


class ToAcademicWarningAssistant(BaseModel):
    """把挂科风险、GPA 风险、补考提醒等问题交给学业预警助手。"""

    request: str = Field(description="学业风险分析需求；如果用户给出学号，需要一并传入。")


academic_warning_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "你是学业预警助手，负责分析低分、挂科、需补考、低 GPA、休学等学业风险。"
            "涉及具体学生风险时，必须调用 analyze_academic_warning 工具。"
            "回答时先说明风险等级，再列出风险课程或状态，最后给出可执行建议。"
            "如果问题不属于学业预警，请调用 CompleteOrEscalate 交还主助手。"
            "\n\n当前学生上下文：\n<StudentInfo>\n{user_info}\n</StudentInfo>"
            "\n当前时间：{time}。",
        ),
        ("placeholder", "{messages}"),
    ]
).partial(time=datetime.now())


academic_warning_tools = [analyze_academic_warning, CompleteOrEscalate]
academic_warning_runnable = academic_warning_prompt | llm.bind_tools(academic_warning_tools)
academic_warning_assistant = Assistant(academic_warning_runnable)
