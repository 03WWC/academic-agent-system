"""chat_service 同步与流式路径的集成测试。

用假图替换 multi_agentic_graph，只验证服务自身的逻辑：
事件过滤、工具事件去重、操作日志写入、兜底回复与异常处理。
不需要真实大模型，也不需要网络。
"""

import asyncio
import unittest
from unittest import mock

from langchain_core.messages import AIMessage

from customer_support_chat.app.services import chat_service


class _Chunk:
    """模拟 AIMessageChunk，被测代码只用到 content 属性。"""

    def __init__(self, content):
        self.content = content


class _FakeGraph:
    """只实现被测代码用到的方法。"""

    def __init__(self, events=None, error=None):
        self._events = events or []
        self._error = error

    async def astream_events(self, inputs, config, version=None):
        if self._error is not None:
            raise self._error
        for event in self._events:
            yield event

    def stream(self, inputs, config, stream_mode=None):
        if self._error is not None:
            raise self._error
        for event in self._events:
            yield event


def _token_event(node, text):
    """构造一个模型流式输出事件。"""
    return {
        "event": "on_chat_model_stream",
        "metadata": {"langgraph_node": node},
        "data": {"chunk": _Chunk(text)},
    }


def _tool_start_event(name, run_id, tool_input):
    return {
        "event": "on_tool_start",
        "name": name,
        "run_id": run_id,
        "data": {"input": tool_input},
    }


def _tool_end_event(name, output):
    return {"event": "on_tool_end", "name": name, "data": {"output": output}}


class _ChatServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.logs = []
        chat_service.set_operation_log_sink(
            lambda session_id, entry: self.logs.append((session_id, entry))
        )
        self.session = {"session_id": "s-1", "config": {"thread_id": "t-1"}}

    def tearDown(self):
        chat_service.set_operation_log_sink(None)

    def _log_types(self):
        return [entry["type"] for _, entry in self.logs]

    def _collect(self, graph):
        with mock.patch.object(chat_service, "multi_agentic_graph", graph):
            return asyncio.run(
                self._aiter(chat_service.stream_user_message(self.session, "你好"))
            )

    def _process(self, graph):
        with mock.patch.object(chat_service, "multi_agentic_graph", graph):
            return asyncio.run(chat_service.process_user_message(self.session, "你好"))

    @staticmethod
    async def _aiter(agen):
        return [event async for event in agen]


class StreamUserMessageTest(_ChatServiceTestCase):
    def test_tokens_from_academic_assistants_are_streamed(self):
        graph = _FakeGraph(
            [
                _token_event("primary_assistant", "你好"),
                _token_event("student_profile_assistant", "，同学"),
            ]
        )

        events = self._collect(graph)

        self.assertEqual(
            [e["content"] for e in events if e["type"] == "token"], ["你好", "，同学"]
        )
        self.assertEqual(events[-1], {"type": "final", "content": "你好，同学"})

    def test_tokens_from_non_academic_nodes_are_filtered_out(self):
        """护栏节点的结构化输出不能流给前端。"""
        graph = _FakeGraph(
            [
                _token_event("guardrail_check", '{"is_safe": true}'),
                _token_event("primary_assistant", "正常回复"),
            ]
        )

        events = self._collect(graph)

        tokens = [e["content"] for e in events if e["type"] == "token"]
        self.assertEqual(tokens, ["正常回复"])
        self.assertNotIn("is_safe", "".join(tokens))

    def test_tool_events_are_logged_once_per_run(self):
        graph = _FakeGraph(
            [
                _tool_start_event("get_student_profile", "r-1", {"student_id": "20240001"}),
                _tool_start_event("get_student_profile", "r-1", {"student_id": "20240001"}),
                _tool_end_event("get_student_profile", "王小明 在读"),
                _token_event("primary_assistant", "已查到"),
            ]
        )

        self._collect(graph)

        self.assertEqual(
            self._log_types(), ["user_input", "tool_call", "tool_result", "ai_response"]
        )

    def test_empty_model_output_falls_back_to_friendly_message(self):
        events = self._collect(_FakeGraph([]))

        self.assertEqual(events[0]["type"], "token")
        self.assertIn("换一种说法", events[0]["content"])
        self.assertEqual(events[-1]["type"], "final")
        self.assertIn("换一种说法", events[-1]["content"])

    def test_graph_failure_yields_error_event_and_logs_it(self):
        events = self._collect(_FakeGraph(error=RuntimeError("模型调用失败")))

        self.assertEqual(events[-1]["type"], "error")
        self.assertEqual(self._log_types(), ["user_input", "error"])


class ProcessUserMessageTest(_ChatServiceTestCase):
    def test_returns_latest_ai_message(self):
        graph = _FakeGraph(
            [
                {"messages": [AIMessage(content="第一句")]},
                {"messages": [AIMessage(content="最终回复")]},
            ]
        )

        self.assertEqual(self._process(graph), "最终回复")
        self.assertEqual(self._log_types(), ["user_input", "ai_response"])

    def test_returns_fallback_when_no_ai_message(self):
        result = self._process(_FakeGraph([]))

        self.assertIn("换一种说法", result)

    def test_graph_failure_returns_friendly_error(self):
        result = self._process(_FakeGraph(error=RuntimeError("模型调用失败")))

        self.assertIn("稍后再试", result)
        self.assertEqual(self._log_types(), ["user_input", "error"])


if __name__ == "__main__":
    unittest.main()
