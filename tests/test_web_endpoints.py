"""Web 层接口测试。

Web 层此前完全没有测试覆盖，而它是用户唯一直接接触的部分。
这里用 FastAPI TestClient 覆盖不依赖大模型调用的端点：
主页渲染、待审批查询、操作日志查询。
"""

import json
import unittest
import warnings
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from web_app.app import main as web_app_main
from web_app.app.main import app


class WebEndpointsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_index_page_renders_html(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])

    def test_index_page_returns_session_cookie(self):
        response = self.client.get("/")

        self.assertIn("session_id", response.cookies)

    def test_pending_action_is_none_for_new_session(self):
        response = self.client.get("/pending-action")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["pending_action"])

    def test_operation_log_is_empty_for_new_session(self):
        response = self.client.get("/operation-log")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["operation_log"], [])

    def test_index_page_does_not_use_deprecated_template_signature(self):
        """Starlette 已废弃 TemplateResponse(name, context) 的旧签名。

        只针对这一条告警断言，避免被第三方库的其他 DeprecationWarning 干扰。
        """
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            response = self.client.get("/")

        self.assertEqual(response.status_code, 200)

        offenders = [
            str(w.message)
            for w in caught
            if issubclass(w.category, DeprecationWarning)
            and "first parameter" in str(w.message)
        ]
        self.assertEqual(offenders, [], f"主页仍在用废弃的模板签名：{offenders}")


class ChatEndpointTest(unittest.TestCase):
    """覆盖聊天端点：NDJSON 流式协议、非流式兼容接口与聊天历史落盘。"""

    def setUp(self):
        self.client = TestClient(app)

    @staticmethod
    def _fake_stream(*events):
        """构造一个假的流式生成器，替代真实的大模型调用。"""

        async def _streamer(session_data, message):
            for event in events:
                yield event

        return _streamer

    def test_chat_returns_agent_response(self):
        async def fake_process(session_data, message):
            return f"收到：{message}"

        with mock.patch.object(web_app_main, "process_user_message", fake_process):
            response = self.client.post("/chat", json={"message": "补考什么时候截止"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"response": "收到：补考什么时候截止"})

    def test_chat_stream_speaks_ndjson(self):
        streamer = self._fake_stream(
            {"type": "token", "content": "你好"},
            {"type": "token", "content": "，同学"},
            {"type": "final", "content": "你好，同学"},
        )

        with mock.patch.object(web_app_main, "stream_user_message", streamer):
            response = self.client.post("/chat/stream", json={"message": "你好"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("application/x-ndjson", response.headers["content-type"])

        events = [json.loads(line) for line in response.text.strip().splitlines()]
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0], {"type": "token", "content": "你好"})
        self.assertEqual(events[-1], {"type": "final", "content": "你好，同学"})

    def test_chat_stream_keeps_chinese_readable(self):
        """NDJSON 用 ensure_ascii=False，中文不应被转义成 \\uXXXX。"""
        streamer = self._fake_stream({"type": "final", "content": "已受理你的请假申请"})

        with mock.patch.object(web_app_main, "stream_user_message", streamer):
            response = self.client.post("/chat/stream", json={"message": "请假"})

        self.assertIn("已受理你的请假申请", response.text)
        self.assertNotIn("\\u", response.text)

    def test_chat_stream_persists_chat_history(self):
        self.client.get("/")  # 先建立会话 Cookie
        session_id = self.client.cookies.get("session_id")
        self.assertIsNotNone(session_id)

        session_file = Path("user_data") / f"{session_id}.json"
        self.addCleanup(lambda: session_file.exists() and session_file.unlink())

        streamer = self._fake_stream({"type": "final", "content": "已记录的回答"})

        with mock.patch.object(web_app_main, "stream_user_message", streamer):
            response = self.client.post("/chat/stream", json={"message": "我的问题"})

        self.assertEqual(response.status_code, 200)

        history = json.loads(session_file.read_text(encoding="utf-8"))["chat_history"]
        self.assertEqual(history[-1]["user_message"], "我的问题")
        self.assertEqual(history[-1]["ai_response"], "已记录的回答")


if __name__ == "__main__":
    unittest.main()
