from datetime import datetime

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from customer_support_chat.app.services.assistants.assistant_base import (
    Assistant,
    CompleteOrEscalate,
    llm,
)
from customer_support_chat.app.services.tools.tickets import (
    create_academic_ticket,
    search_academic_tickets,
)


class ToTicketAssistant(BaseModel):
    """把请假、补考、成绩复核、申诉等工单创建和查询交给工单助手。"""

    request: str = Field(description="工单处理需求；需要保留学号、申请类型、标题或查询意图。")


ticket_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "你是教务工单助手，负责创建和查询请假、补考、成绩复核、申诉等教务工单。"
            "创建工单前必须确认学号、申请类型和标题；信息完整后调用 create_academic_ticket。"
            "查询已有工单时调用 search_academic_tickets。"
            "如果用户还没有给全信息，只追问最关键的缺失项。"
            "如果问题不属于工单处理，请调用 CompleteOrEscalate 交还主助手。"
            "\n\n当前学生上下文：\n<StudentInfo>\n{user_info}\n</StudentInfo>"
            "\n当前时间：{time}。",
        ),
        ("placeholder", "{messages}"),
    ]
).partial(time=datetime.now())


ticket_tools = [create_academic_ticket, search_academic_tickets, CompleteOrEscalate]
ticket_runnable = ticket_prompt | llm.bind_tools(ticket_tools)
ticket_assistant = Assistant(ticket_runnable)
