"""Assistant 空回复重试逻辑的测试。

Assistant.__call__ 在模型返回空内容时会补一句提示重新询问模型。
这段逻辑此前没有测试覆盖，而它原来的 while True 循环没有次数上限：
模型持续返回空内容时会无限循环（请求永不返回、持续产生大模型调用费用）。
"""

import unittest

from langchain_core.messages import AIMessage, HumanMessage

from customer_support_chat.app.services.assistants.assistant_base import Assistant


class _FakeRunnable:
    """按脚本返回结果，并记录调用次数与每次收到的状态。"""

    def __init__(self, replies, hard_limit=20):
        self._replies = list(replies)
        self._hard_limit = hard_limit
        self.calls = 0
        self.states = []

    def invoke(self, state, config=None):
        self.calls += 1
        self.states.append(state)
        if self.calls > self._hard_limit:
            raise RuntimeError("循环没有终止：调用次数超过硬上限")
        index = min(self.calls, len(self._replies)) - 1
        return self._replies[index]


def _state():
    return {"messages": [HumanMessage(content="补考什么时候截止")]}


class AssistantCallTest(unittest.TestCase):
    def test_readable_reply_returns_immediately(self):
        runnable = _FakeRunnable([AIMessage(content="开学后两周内提交申请。")])

        result = Assistant(runnable)(_state())

        self.assertEqual(runnable.calls, 1)
        self.assertEqual(result["messages"].content, "开学后两周内提交申请。")

    def test_empty_reply_triggers_one_retry(self):
        runnable = _FakeRunnable(
            [AIMessage(content=""), AIMessage(content="这是正常回复。")]
        )

        result = Assistant(runnable)(_state())

        self.assertEqual(runnable.calls, 2)
        self.assertEqual(result["messages"].content, "这是正常回复。")

    def test_retry_appends_a_nudge_message(self):
        runnable = _FakeRunnable([AIMessage(content=""), AIMessage(content="好的。")])

        Assistant(runnable)(_state())

        retry_messages = runnable.states[1]["messages"]
        self.assertEqual(len(retry_messages), 2)
        self.assertIn("请给出真实、可读的中文回复", retry_messages[-1][1])

    def test_tool_calls_are_accepted_without_text(self):
        runnable = _FakeRunnable(
            [
                AIMessage(
                    content="",
                    tool_calls=[
                        {"id": "call-0", "name": "get_student_profile", "args": {}}
                    ],
                )
            ]
        )

        result = Assistant(runnable)(_state())

        self.assertEqual(runnable.calls, 1)
        self.assertEqual(result["messages"].tool_calls[0]["name"], "get_student_profile")

    def test_persistent_empty_replies_do_not_loop_forever(self):
        """模型一直返回空内容时必须有次数上限。

        旧实现没有计数器，会无限循环：请求永不返回、工作线程被占死，
        并且每一次循环都是一次真实的大模型调用。
        """
        runnable = _FakeRunnable([AIMessage(content="")], hard_limit=20)

        Assistant(runnable)(_state())

        self.assertLessEqual(runnable.calls, 3, "空回复重试没有次数上限")


if __name__ == "__main__":
    unittest.main()
