from datetime import datetime

from langchain_core.prompts import ChatPromptTemplate

from customer_support_chat.app.services.assistants.academic_warning_assistant import (
    ToAcademicWarningAssistant,
)
from customer_support_chat.app.services.assistants.course_policy_assistant import (
    ToCoursePolicyAssistant,
)
from customer_support_chat.app.services.assistants.assistant_base import Assistant, llm
from customer_support_chat.app.services.assistants.student_profile_assistant import (
    ToStudentProfileAssistant,
)
from customer_support_chat.app.services.assistants.ticket_assistant import (
    ToTicketAssistant,
)


primary_assistant_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "你是教务多 Agent 学生服务系统的主助手。"
            "你的职责不是直接处理所有细节，而是识别用户意图，并把问题委派给合适的专业助手。"
            "\n\n委派规则："
            "\n- 学号、姓名、专业、年级、学籍状态、GPA、导师、课程状态，调用 ToStudentProfileAssistant。"
            "\n- 补考、缓考、退课、选课、成绩复核等政策规则，调用 ToCoursePolicyAssistant。"
            "\n- 挂科风险、低分、低 GPA、需补考、休学风险，调用 ToAcademicWarningAssistant。"
            "\n- 请假申请、补考申请、成绩复核申请、申诉、工单查询，调用 ToTicketAssistant。"
            "\n- 不要告诉用户你在切换助手，只需要自然地继续服务。"
            "\n- 如果用户问题不清楚，先追问一个最关键的问题。"
            "\n\n当前学生上下文：\n<StudentInfo>\n{user_info}\n</StudentInfo>"
            "\n当前时间：{time}。",
        ),
        ("placeholder", "{messages}"),
    ]
).partial(time=datetime.now())


# 主助手只保留教务方向委派工具，避免运行时加载历史业务依赖。
primary_assistant_tools = [
    ToStudentProfileAssistant,
    ToCoursePolicyAssistant,
    ToAcademicWarningAssistant,
    ToTicketAssistant,
]

primary_assistant_runnable = primary_assistant_prompt | llm.bind_tools(
    primary_assistant_tools
)

primary_assistant = Assistant(primary_assistant_runnable)
