"""助手工具绑定的测试。

README 声称「每个专业助手只绑定自己需要的工具」，这里把这条设计约束固定下来：
既要防止工具越界绑定，也要保证主助手的委派工具与路由函数保持一致。
"""

import unittest

from langchain_core.messages import AIMessage

from customer_support_chat.app.graph import (
    academic_warning_tools,
    course_policy_tools,
    primary_assistant_tools,
    route_primary_assistant,
    student_profile_tools,
    ticket_tools,
)

ESCALATION_TOOL = "CompleteOrEscalate"

SPECIALIST_TOOLS = {
    "student_profile": student_profile_tools,
    "course_policy": course_policy_tools,
    "academic_warning": academic_warning_tools,
    "ticket": ticket_tools,
}


def _tool_names(tools):
    return {getattr(tool, "name", None) or tool.__name__ for tool in tools}


class SpecialistToolBindingTest(unittest.TestCase):
    def test_each_specialist_binds_exactly_its_own_tool(self):
        expected = {
            "student_profile": {"get_student_profile"},
            "course_policy": {"lookup_academic_policy"},
            "academic_warning": {"analyze_academic_warning"},
            "ticket": {"create_academic_ticket", "search_academic_tickets"},
        }

        for specialist, tools in SPECIALIST_TOOLS.items():
            with self.subTest(specialist=specialist):
                self.assertEqual(
                    _tool_names(tools), expected[specialist] | {ESCALATION_TOOL}
                )

    def test_specialists_cannot_reach_each_others_tools(self):
        owned = {
            specialist: _tool_names(tools) - {ESCALATION_TOOL}
            for specialist, tools in SPECIALIST_TOOLS.items()
        }

        for specialist, tools in owned.items():
            others = set().union(
                *(owned[other] for other in owned if other != specialist)
            )
            with self.subTest(specialist=specialist):
                self.assertEqual(
                    tools & others,
                    set(),
                    f"{specialist} 绑定了其它助手的工具：{sorted(tools & others)}",
                )

    def test_every_specialist_can_hand_control_back(self):
        for specialist, tools in SPECIALIST_TOOLS.items():
            with self.subTest(specialist=specialist):
                self.assertIn(ESCALATION_TOOL, _tool_names(tools))


class PrimaryAssistantDelegationTest(unittest.TestCase):
    def test_primary_assistant_binds_exactly_four_delegation_tools(self):
        self.assertEqual(len(primary_assistant_tools), 4)

    def test_every_delegation_tool_is_routable(self):
        """路由函数必须认识所有绑定给主助手的委派工具。

        漏掉一个的话，模型发出该委派调用时会被落到 primary_assistant_tools，
        委派静默失效 —— 既不报错，也永远进不了对应专业助手。
        """
        for tool in primary_assistant_tools:
            tool_name = tool.__name__
            state = {
                "messages": [
                    AIMessage(
                        content="",
                        tool_calls=[{"id": "call-0", "name": tool_name, "args": {}}],
                    )
                ]
            }
            with self.subTest(tool=tool_name):
                route = route_primary_assistant(state)
                self.assertNotEqual(
                    route,
                    "primary_assistant_tools",
                    f"{tool_name} 没有对应的入口节点，委派会静默失效",
                )

    def test_specialists_do_not_bind_delegation_tools(self):
        """专业助手不应再往下委派，只负责处理本领域任务。"""
        delegation_names = {tool.__name__ for tool in primary_assistant_tools}

        for specialist, tools in SPECIALIST_TOOLS.items():
            with self.subTest(specialist=specialist):
                self.assertEqual(_tool_names(tools) & delegation_names, set())


if __name__ == "__main__":
    unittest.main()
