"""Web 层会话数据管理的测试。

user_data_manager 负责会话、聊天历史、待审批操作与操作日志的本地持久化，
是所有 Web 请求都会经过的一层，此前完全没有测试覆盖。

测试通过把 USER_DATA_DIR 指向临时目录来隔离文件系统，不污染真实的 ./user_data。
"""

import json
import tempfile
import unittest
from pathlib import Path

from web_app.app.core import user_data_manager


class UserDataManagerTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._original_dir = user_data_manager.USER_DATA_DIR
        user_data_manager.USER_DATA_DIR = self._tmp.name

    def tearDown(self):
        user_data_manager.USER_DATA_DIR = self._original_dir
        self._tmp.cleanup()

    def _session_file(self, session_id: str) -> Path:
        return Path(self._tmp.name) / f"{session_id}.json"

    # --- 会话生命周期 ---

    def test_get_user_session_creates_default_session(self):
        session = user_data_manager.get_user_session("s-1")

        self.assertEqual(session["session_id"], "s-1")
        self.assertEqual(session["chat_history"], [])
        self.assertIsNone(session["pending_action"])
        self.assertIsNone(session["user_decision"])
        self.assertEqual(session["operation_log"], [])
        self.assertIn("created_at", session)

    def test_get_user_session_persists_to_disk(self):
        user_data_manager.get_user_session("s-1")

        self.assertTrue(self._session_file("s-1").exists())

    def test_get_user_session_returns_existing_data(self):
        user_data_manager.update_user_chat_history("s-1", "问题", "回答")

        session = user_data_manager.get_user_session("s-1")

        self.assertEqual(len(session["chat_history"]), 1)
        self.assertEqual(session["chat_history"][0]["user_message"], "问题")

    def test_load_user_data_returns_empty_dict_when_missing(self):
        self.assertEqual(user_data_manager.load_user_data("不存在"), {})

    # --- 聊天历史 ---

    def test_update_user_chat_history_appends_entries(self):
        user_data_manager.update_user_chat_history("s-1", "问题一", "回答一")
        user_data_manager.update_user_chat_history("s-1", "问题二", "回答二")

        history = user_data_manager.load_user_data("s-1")["chat_history"]

        self.assertEqual(len(history), 2)
        self.assertEqual(history[-1]["user_message"], "问题二")
        self.assertEqual(history[-1]["ai_response"], "回答二")
        self.assertIn("timestamp", history[-1])

    # --- 待审批操作 ---

    def test_pending_action_lifecycle(self):
        self.assertIsNone(user_data_manager.get_pending_action("s-1"))

        user_data_manager.set_pending_action("s-1", {"tool": "create_ticket"})
        self.assertEqual(
            user_data_manager.get_pending_action("s-1"), {"tool": "create_ticket"}
        )

        user_data_manager.clear_pending_action("s-1")
        self.assertIsNone(user_data_manager.get_pending_action("s-1"))

    # --- 用户决策 ---

    def test_user_decision_lifecycle(self):
        self.assertIsNone(user_data_manager.get_user_decision("s-1"))

        user_data_manager.set_user_decision("s-1", "approve")
        self.assertEqual(user_data_manager.get_user_decision("s-1"), "approve")

        user_data_manager.clear_user_decision("s-1")
        self.assertIsNone(user_data_manager.get_user_decision("s-1"))

    # --- 操作日志 ---

    def test_add_operation_log_stamps_timestamp(self):
        user_data_manager.add_operation_log("s-1", {"type": "tool_call"})

        log = user_data_manager.get_operation_log("s-1")

        self.assertEqual(len(log), 1)
        self.assertEqual(log[0]["type"], "tool_call")
        self.assertIn("timestamp", log[0])

    def test_add_operation_log_keeps_provided_timestamp(self):
        user_data_manager.add_operation_log("s-1", {"type": "x", "timestamp": "固定值"})

        self.assertEqual(
            user_data_manager.get_operation_log("s-1")[0]["timestamp"], "固定值"
        )

    def test_get_operation_log_returns_most_recent_entries(self):
        for index in range(5):
            user_data_manager.add_operation_log("s-1", {"type": f"event-{index}"})

        recent = user_data_manager.get_operation_log("s-1", limit=2)

        self.assertEqual([entry["type"] for entry in recent], ["event-3", "event-4"])

    def test_clear_operation_log(self):
        user_data_manager.add_operation_log("s-1", {"type": "tool_call"})

        user_data_manager.clear_operation_log("s-1")

        self.assertEqual(user_data_manager.get_operation_log("s-1"), [])

    def test_session_is_stored_as_readable_json(self):
        user_data_manager.get_user_session("s-1")

        raw = self._session_file("s-1").read_text(encoding="utf-8")

        self.assertEqual(json.loads(raw)["session_id"], "s-1")


if __name__ == "__main__":
    unittest.main()
