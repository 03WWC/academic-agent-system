from datetime import datetime

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from customer_support_chat.app.services.assistants.assistant_base import (
    Assistant,
    CompleteOrEscalate,
    llm,
)
from customer_support_chat.app.services.tools.academic_policy import lookup_academic_policy


class ToCoursePolicyAssistant(BaseModel):
    """把补考、缓考、退课、选课、成绩复核等政策问题交给课程政策助手。"""

    request: str = Field(description="课程或教务政策问题，需要保留用户提到的政策主题和时间线索。")


course_policy_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "你是课程与教务政策助手，负责回答补考、缓考、退课、选课、成绩复核等规则问题。"
            "你必须调用 lookup_academic_policy 检索政策依据，再根据结果用中文总结。"
            "回答时先给结论，再说明依据和下一步材料或截止时间。"
            "如果问题不是政策类问题，请调用 CompleteOrEscalate 交还主助手。"
            "\n\n当前学生上下文：\n<StudentInfo>\n{user_info}\n</StudentInfo>"
            "\n当前时间：{time}。",
        ),
        ("placeholder", "{messages}"),
    ]
).partial(time=datetime.now())


course_policy_tools = [lookup_academic_policy, CompleteOrEscalate]
course_policy_runnable = course_policy_prompt | llm.bind_tools(course_policy_tools)
course_policy_assistant = Assistant(course_policy_runnable)
