"""全部助手提示词的测试。

5 个助手（主助手 + 4 个专业助手）的提示词里都带「当前时间：{time}」，
用于判断补考、退课、成绩复核等相对期限。这里统一固定它们必须每次格式化
都重新读时钟——只测其中一个是不够的，这个缺陷当时就是 5 处同源。

模块用 importlib 按完整路径加载：assistants/__init__.py 把同名的 Assistant
实例导进了包命名空间，直接 from ...assistants import primary_assistant
拿到的是实例而不是模块。
"""

import importlib
import re
import unittest
from unittest import mock

from customer_support_chat.app.graph import (
    academic_warning_tools,
    course_policy_tools,
    primary_assistant_tools,
    student_profile_tools,
    ticket_tools,
)

TIME_PATTERN = re.compile(r"当前时间：([^。]+)。")


def _tool_names(tools):
    return {getattr(tool, "name", None) or tool.__name__ for tool in tools}


BOUND_TOOLS = {
    "primary_assistant": _tool_names(primary_assistant_tools),
    "student_profile": _tool_names(student_profile_tools),
    "course_policy": _tool_names(course_policy_tools),
    "academic_warning": _tool_names(academic_warning_tools),
    "ticket": _tool_names(ticket_tools),
}

# 助手名 -> (模块完整路径, 提示词属性名)
ASSISTANT_PROMPTS = {
    "primary_assistant": (
        "customer_support_chat.app.services.assistants.primary_assistant",
        "primary_assistant_prompt",
    ),
    "student_profile": (
        "customer_support_chat.app.services.assistants.student_profile_assistant",
        "student_profile_prompt",
    ),
    "course_policy": (
        "customer_support_chat.app.services.assistants.course_policy_assistant",
        "course_policy_prompt",
    ),
    "academic_warning": (
        "customer_support_chat.app.services.assistants.academic_warning_assistant",
        "academic_warning_prompt",
    ),
    "ticket": (
        "customer_support_chat.app.services.assistants.ticket_assistant",
        "ticket_prompt",
    ),
}


class _FakeClock:
    """可控时钟：now() 返回被测试临时设定的值。"""

    current = "未设定"

    @classmethod
    def now(cls):
        return cls.current


def _render(prompt, user_info="王小明，人工智能专业"):
    return prompt.format_messages(messages=[], user_info=user_info)[0].content


class AssistantPromptTest(unittest.TestCase):
    def _prompts(self):
        for name, (module_path, attribute) in ASSISTANT_PROMPTS.items():
            module = importlib.import_module(module_path)
            yield name, module, getattr(module, attribute)

    def test_every_prompt_renders_student_context_and_time(self):
        for name, _, prompt in self._prompts():
            with self.subTest(prompt=name):
                text = _render(prompt)
                self.assertIn("王小明，人工智能专业", text)
                match = TIME_PATTERN.search(text)
                self.assertIsNotNone(match, f"{name} 没有渲染出当前时间")
                self.assertTrue(match.group(1).strip())

    def test_time_is_bound_as_a_callable(self):
        """{time} 必须以 callable 形式绑定。

        写死成 .partial(time=datetime.now()) 只会在导入时求值一次。
        """
        for name, _, prompt in self._prompts():
            with self.subTest(prompt=name):
                self.assertTrue(
                    callable(prompt.partial_variables.get("time")),
                    f"{name} 的 time 不是 callable，会被固定在导入时刻",
                )

    def test_current_time_is_read_from_the_clock_on_every_format(self):
        """每次格式化都必须重新读时钟。

        这里用可控时钟替身，而不是比较两次真实调用的时间戳：
        Windows 的时钟粒度比微秒粗，连续两次调用可能落在同一刻度上，
        那样断言永远「相等」，测不出任何东西。
        """
        for name, module, prompt in self._prompts():
            with self.subTest(prompt=name):
                with mock.patch.object(module, "datetime", _FakeClock):
                    _FakeClock.current = "第一次读取"
                    first = TIME_PATTERN.search(_render(prompt)).group(1)
                    _FakeClock.current = "第二次读取"
                    second = TIME_PATTERN.search(_render(prompt)).group(1)

                self.assertEqual(first, "第一次读取")
                self.assertEqual(second, "第二次读取")


class PromptToolConsistencyTest(unittest.TestCase):
    """提示词与工具绑定必须双向一致。

    提示词写着「必须调用 xxx 工具」却没有绑定，模型就会去调一个不存在的工具；
    反过来，绑定了却从没在提示词里提过，模型也不知道该用它。
    这两种不一致靠人眼 review 很容易漏。
    """

    def _prompts(self):
        for name, (module_path, attribute) in ASSISTANT_PROMPTS.items():
            module = importlib.import_module(module_path)
            yield name, getattr(module, attribute)

    def test_prompt_never_mentions_a_tool_that_is_not_bound(self):
        every_tool = set().union(*BOUND_TOOLS.values())

        for name, prompt in self._prompts():
            text = _render(prompt)
            mentioned = {tool for tool in every_tool if tool in text}

            with self.subTest(prompt=name):
                self.assertTrue(
                    mentioned <= BOUND_TOOLS[name],
                    f"{name} 的提示词提到了未绑定的工具："
                    f"{sorted(mentioned - BOUND_TOOLS[name])}",
                )

    def test_every_bound_tool_is_mentioned_in_its_prompt(self):
        for name, prompt in self._prompts():
            text = _render(prompt)
            unmentioned = {tool for tool in BOUND_TOOLS[name] if tool not in text}

            with self.subTest(prompt=name):
                self.assertEqual(
                    unmentioned, set(), f"{name} 绑定了但提示词没提到的工具：{sorted(unmentioned)}"
                )


if __name__ == "__main__":
    unittest.main()
