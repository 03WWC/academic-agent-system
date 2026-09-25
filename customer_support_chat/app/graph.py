from typing import Literal

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import tools_condition

from customer_support_chat.app.core.logger import logger
from customer_support_chat.app.core.state import State
from customer_support_chat.app.services.assistants.academic_warning_assistant import (
    ToAcademicWarningAssistant,
    academic_warning_assistant,
    academic_warning_tools,
)
from customer_support_chat.app.services.assistants.course_policy_assistant import (
    ToCoursePolicyAssistant,
    course_policy_assistant,
    course_policy_tools,
)
from customer_support_chat.app.services.assistants.primary_assistant import (
    primary_assistant,
    primary_assistant_tools,
)
from customer_support_chat.app.services.assistants.student_profile_assistant import (
    ToStudentProfileAssistant,
    student_profile_assistant,
    student_profile_tools,
)
from customer_support_chat.app.services.assistants.ticket_assistant import (
    ToTicketAssistant,
    ticket_assistant,
    ticket_tools,
)
from customer_support_chat.app.services.guardrails.guardrail_agents import (
    jailbreak_guardrail_agent,
    jailbreak_guardrail_agent_instructions,
    relevance_guardrail_agent,
    relevance_guardrail_agent_instructions,
)
from customer_support_chat.app.services.tools.students import get_student_profile
from customer_support_chat.app.services.utils import (
    create_entry_node,
    create_tool_node_with_fallback,
)


builder = StateGraph(State)


def user_info(state: State, config: RunnableConfig):
    """读取当前会话绑定的学生档案，写入 LangGraph 状态。"""
    configuration = config.get("configurable", {})
    student_id = configuration.get("student_id", "20240001")
    user_info_str = get_student_profile.invoke({"student_id": student_id})
    return {"user_info": user_info_str}


builder.add_node("fetch_user_info", user_info)


def guardrail_check(state: State, config: RunnableConfig):
    """检查用户输入是否安全、是否属于教务服务范围。"""
    user_messages = [msg for msg in state["messages"] if isinstance(msg, HumanMessage)]
    if not user_messages:
        logger.warning("没有找到用户输入，跳过护栏检查。")
        return {"messages": [HumanMessage(content="请先输入你的教务问题。")]}

    user_input = user_messages[-1].content
    logger.info(f"开始检查用户输入：{user_input}")

    # 第一道护栏：检查是否存在越狱或恶意指令。
    jailbreak_prompt = f"{jailbreak_guardrail_agent_instructions}\n\n用户输入：{user_input}"
    jailbreak_result = jailbreak_guardrail_agent.invoke(jailbreak_prompt)
    if not jailbreak_result.is_safe:
        logger.warning(f"发现不安全输入：{jailbreak_result.reasoning}")
        return {
            "messages": [
                HumanMessage(content=f"这个请求我不能协助处理。原因：{jailbreak_result.reasoning}")
            ]
        }

    # 第二道护栏：检查是否与教务、课程、学生服务等主题相关。
    relevance_prompt = f"{relevance_guardrail_agent_instructions}\n\n用户输入：{user_input}"
    relevance_result = relevance_guardrail_agent.invoke(relevance_prompt)
    if not relevance_result.is_relevant:
        logger.warning(f"输入可能不属于教务范围：{relevance_result.reasoning}")

    logger.info("用户输入通过护栏检查。")
    return {"messages": []}


builder.add_node("guardrail_check", guardrail_check)


def should_route_to_primary(state: State) -> bool:
    """判断专业助手是否要求把控制权交还给主助手。"""
    if not state["messages"]:
        return False

    last_message = state["messages"][-1]
    if hasattr(last_message, "content") and isinstance(last_message.content, str):
        return "任务已完成或已交还主助手" in last_message.content
    return False


def add_academic_specialist(
    *,
    enter_node: str,
    assistant_node: str,
    tool_node: str,
    assistant_name: str,
    dialog_state: str,
    assistant,
    tools: list,
):
    """按统一结构注册一个教务专业助手及其工具节点。"""
    builder.add_node(
        enter_node,
        create_entry_node(assistant_name, dialog_state),
    )
    builder.add_node(assistant_node, assistant)
    builder.add_edge(enter_node, assistant_node)
    builder.add_node(tool_node, create_tool_node_with_fallback(tools))

    def route_assistant(state: State) -> str:
        route = tools_condition(state)
        if route == END:
            return END
        return tool_node

    def route_tools(state: State) -> str:
        return "primary_assistant" if should_route_to_primary(state) else assistant_node

    builder.add_conditional_edges(assistant_node, route_assistant)
    builder.add_conditional_edges(tool_node, route_tools)


add_academic_specialist(
    enter_node="enter_student_profile",
    assistant_node="student_profile_assistant",
    tool_node="student_profile_tools",
    assistant_name="Student Profile Assistant",
    dialog_state="student_profile",
    assistant=student_profile_assistant,
    tools=student_profile_tools,
)

add_academic_specialist(
    enter_node="enter_course_policy",
    assistant_node="course_policy_assistant",
    tool_node="course_policy_tools",
    assistant_name="Course Policy Assistant",
    dialog_state="course_policy",
    assistant=course_policy_assistant,
    tools=course_policy_tools,
)

add_academic_specialist(
    enter_node="enter_academic_warning",
    assistant_node="academic_warning_assistant",
    tool_node="academic_warning_tools",
    assistant_name="Academic Warning Assistant",
    dialog_state="academic_warning",
    assistant=academic_warning_assistant,
    tools=academic_warning_tools,
)

add_academic_specialist(
    enter_node="enter_ticket",
    assistant_node="ticket_assistant",
    tool_node="ticket_tools",
    assistant_name="Ticket Assistant",
    dialog_state="ticket",
    assistant=ticket_assistant,
    tools=ticket_tools,
)


# 主助手链路：识别意图后委派给对应教务专业助手。
builder.add_node("primary_assistant", primary_assistant)
builder.add_node(
    "primary_assistant_tools",
    create_tool_node_with_fallback(primary_assistant_tools),
)


def route_primary_assistant(state: State) -> Literal[
    "primary_assistant_tools",
    "enter_student_profile",
    "enter_course_policy",
    "enter_academic_warning",
    "enter_ticket",
    "__end__",
]:
    """根据主助手的委派工具调用，决定进入哪个专业助手。"""
    route = tools_condition(state)
    if route == END:
        return END

    tool_calls = state["messages"][-1].tool_calls
    if not tool_calls:
        return "primary_assistant_tools"

    tool_name = tool_calls[0]["name"]
    if tool_name == ToStudentProfileAssistant.__name__:
        return "enter_student_profile"
    if tool_name == ToCoursePolicyAssistant.__name__:
        return "enter_course_policy"
    if tool_name == ToAcademicWarningAssistant.__name__:
        return "enter_academic_warning"
    if tool_name == ToTicketAssistant.__name__:
        return "enter_ticket"
    return "primary_assistant_tools"


builder.add_conditional_edges(
    "primary_assistant",
    route_primary_assistant,
    {
        "enter_student_profile": "enter_student_profile",
        "enter_course_policy": "enter_course_policy",
        "enter_academic_warning": "enter_academic_warning",
        "enter_ticket": "enter_ticket",
        "primary_assistant_tools": "primary_assistant_tools",
        END: END,
    },
)
builder.add_edge("primary_assistant_tools", "primary_assistant")


# 基础入口：每轮先补学生上下文，再过护栏，再进入主助手。
builder.add_edge(START, "fetch_user_info")
builder.add_edge("fetch_user_info", "guardrail_check")
builder.add_edge("guardrail_check", "primary_assistant")


memory = MemorySaver()
multi_agentic_graph = builder.compile(checkpointer=memory)
