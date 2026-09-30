"""验证操作日志写入器的注入机制。

核心层不再依赖 Web 层，而是由调用方通过 set_operation_log_sink 注入写入器。
这里直接验证这个接缝确实生效（用 _add_log 是因为走公开接口需要真实调用大模型）。
"""

import unittest


class OperationLogSinkTest(unittest.TestCase):
    def _service(self):
        from customer_support_chat.app.services import chat_service

        return chat_service

    def tearDown(self):
        # 每个用例结束后复位，避免影响其它测试。
        self._service().set_operation_log_sink(None)

    def test_sink_receives_log_entries(self):
        service = self._service()
        received = []
        service.set_operation_log_sink(
            lambda session_id, entry: received.append((session_id, entry))
        )

        service._add_log("session-1", {"type": "user_input", "content": "测试消息"})

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0][0], "session-1")
        self.assertEqual(received[0][1]["type"], "user_input")

    def test_add_log_without_sink_does_not_raise(self):
        service = self._service()
        service.set_operation_log_sink(None)

        service._add_log("session-2", {"type": "user_input"})


if __name__ == "__main__":
    unittest.main()
