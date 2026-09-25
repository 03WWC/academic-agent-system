from datetime import datetime

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from customer_support_chat.app.services.assistants.assistant_base import (
    Assistant,
    CompleteOrEscalate,
    llm,
)
from customer_support_chat.app.services.tools.students import get_student_profile


class ToStudentProfileAssistant(BaseModel):
    """把学生档案、学籍状态、GPA、课程状态查询交给学生档案助手。"""

    request: str = Field(description="学生档案查询需求；如果有学号，需要一并传入。")


student_profile_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "你是学生档案查询助手，负责回答学号、姓名、专业、年级、学籍状态、GPA、导师和课程状态相关问题。"
            "涉及具体学生信息时，必须优先调用 get_student_profile 工具，不要编造学生档案。"
            "如果用户没有给出学号，优先使用当前学生上下文；如果仍无法判断，再追问学号。"
            "如果问题超出学生档案范围，请调用 CompleteOrEscalate 交还主助手。"
            "\n\n当前学生上下文：\n<StudentInfo>\n{user_info}\n</StudentInfo>"
            "\n当前时间：{time}。",
        ),
        ("placeholder", "{messages}"),
    ]
).partial(time=datetime.now())


student_profile_tools = [get_student_profile, CompleteOrEscalate]
student_profile_runnable = student_profile_prompt | llm.bind_tools(student_profile_tools)
student_profile_assistant = Assistant(student_profile_runnable)
