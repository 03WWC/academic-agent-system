"""多 Agent 调度逻辑的测试。

覆盖 graph.py 与 services/utils.py 中决定「把请求交给哪个助手」的核心逻辑：
委派工具 → 入口节点、专业助手 → 主助手的交还判断、工具异常兜底。
这些函数此前完全没有测试覆盖。
"""

import unittest

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.graph import END

from customer_support_chat.app.graph import (
    ToAcademicWarningAssistant,
    ToCoursePolicyAssistant,
    ToStudentProfileAssistant,
    ToTicketAssistant,
    multi_agentic_graph,
    route_primary_assistant,
    should_route_to_primary,
)
from customer_support_chat.app.services.utils import (
    create_entry_node,
    create_tool_node_with_fallback,
    handle_tool_error,
)


def _ai_with_tool_calls(*tool_names):
    return {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {"id": f"call-{index}", "name": name, "args": {}}
                    for index, name in enumerate(tool_names)
                ],
            )
        ]
    }


class RoutePrimaryAssistantTest(unittest.TestCase):
    def test_each_delegation_tool_maps_to_its_entry_node(self):
        expected = {
            ToStudentProfileAssistant.__name__: "enter_student_profile",
            ToCoursePolicyAssistant.__name__: "enter_course_policy",
            ToAcademicWarningAssistant.__name__: "enter_academic_warning",
            ToTicketAssistant.__name__: "enter_ticket",
        }

        for tool_name, entry_node in expected.items():
            with self.subTest(tool_name=tool_name):
                self.assertEqual(route_primary_assistant(_ai_with_tool_calls(tool_name)), entry_node)

    def test_plain_tool_call_goes_to_primary_tools(self):
        state = _ai_with_tool_calls("get_student_profile")

        self.assertEqual(route_primary_assistant(state), "primary_assistant_tools")

    def test_reply_without_tool_calls_ends_the_turn(self):
        state = {"messages": [AIMessage(content="你好，有什么可以帮你？")]}

        self.assertEqual(route_primary_assistant(state), END)


class ShouldRouteToPrimaryTest(unittest.TestCase):
    def test_escalation_message_hands_control_back(self):
        state = {
            "messages": [
                ToolMessage(
                    content="任务已完成或已交还主助手。原因：用户改变了需求",
                    tool_call_id="call-0",
                )
            ]
        }

        self.assertTrue(should_route_to_primary(state))

    def test_normal_tool_result_keeps_the_specialist(self):
        state = {
            "messages": [ToolMessage(content="王小明，在读", tool_call_id="call-0")]
        }

        self.assertFalse(should_route_to_primary(state))

    def test_empty_messages_does_not_route(self):
        self.assertFalse(should_route_to_primary({"messages": []}))


class CreateEntryNodeTest(unittest.TestCase):
    def test_reuses_tool_call_id_from_delegation(self):
        entry_node = create_entry_node("Student Profile Assistant", "student_profile")

        result = entry_node(_ai_with_tool_calls(ToStudentProfileAssistant.__name__))

        self.assertEqual(result["dialog_state"], "student_profile")
        self.assertEqual(len(result["messages"]), 1)
        self.assertEqual(result["messages"][0].tool_call_id, "call-0")

    def test_falls_back_when_no_tool_calls_present(self):
        entry_node = create_entry_node("Ticket Assistant", "ticket")

        result = entry_node({"messages": [AIMessage(content="普通回复")]})

        self.assertEqual(result["messages"][0].tool_call_id, "fallback_tool_call_id")
        self.assertEqual(result["dialog_state"], "ticket")


class HandleToolErrorTest(unittest.TestCase):
    def test_builds_one_tool_message_per_failed_call(self):
        state = {
            "error": RuntimeError("数据库连接失败"),
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {"id": "call-a", "name": "get_student_profile", "args": {}},
                        {"id": "call-b", "name": "search_academic_tickets", "args": {}},
                    ],
                )
            ],
        }

        result = handle_tool_error(state)

        self.assertEqual(
            [message["tool_call_id"] for message in result["messages"]],
            ["call-a", "call-b"],
        )
        self.assertIn("数据库连接失败", result["messages"][0]["content"])


class ToolNodeWithFallbackTest(unittest.TestCase):
    """在最小图里真实执行工具节点。

    裸调 ToolNode 会因缺少图运行时 config 而失败，所以这里搭一个小图来跑。
    """

    @staticmethod
    def _build_graph():
        from langchain_core.tools import tool
        from langgraph.graph import END, START, StateGraph

        from customer_support_chat.app.core.state import State

        @tool
        def echo(text: str) -> str:
            """原样返回输入文本。"""
            return f"回显：{text}"

        builder = StateGraph(State)
        builder.add_node("tools", create_tool_node_with_fallback([echo]))
        builder.add_edge(START, "tools")
        builder.add_edge("tools", END)
        return builder.compile()

    def _invoke_with_args(self, args):
        state = {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[{"id": "call-0", "name": "echo", "args": args}],
                )
            ]
        }
        return self._build_graph().invoke(state)["messages"][-1]

    def test_executes_a_registered_tool(self):
        message = self._invoke_with_args({"text": "你好"})

        self.assertIsInstance(message, ToolMessage)
        self.assertEqual(message.content, "回显：你好")

    def test_bad_arguments_still_return_a_tool_message(self):
        """参数不合法时也必须回一条 ToolMessage。

        否则模型的 tool_call 响应链断裂，整轮对话就卡死了。
        """
        message = self._invoke_with_args({})

        self.assertIsInstance(message, ToolMessage)
        self.assertEqual(message.tool_call_id, "call-0")
        self.assertTrue(message.content.strip())


class GraphStructureTest(unittest.TestCase):
    def test_graph_contains_all_academic_nodes(self):
        nodes = set(multi_agentic_graph.get_graph().nodes)

        expected = {
            "fetch_user_info",
            "guardrail_check",
            "primary_assistant",
            "primary_assistant_tools",
        }
        for specialist in (
            "student_profile",
            "course_policy",
            "academic_warning",
            "ticket",
        ):
            expected.add(f"enter_{specialist}")
            expected.add(f"{specialist}_assistant")
            expected.add(f"{specialist}_tools")

        self.assertTrue(
            expected.issubset(nodes), f"缺少节点：{sorted(expected - nodes)}"
        )


if __name__ == "__main__":
    unittest.main()
