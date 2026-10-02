"""Web 层接口测试。

Web 层此前完全没有测试覆盖，而它是用户唯一直接接触的部分。
这里用 FastAPI TestClient 覆盖不依赖大模型调用的端点：
主页渲染、待审批查询、操作日志查询。
"""

import unittest
import warnings

from fastapi.testclient import TestClient

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


if __name__ == "__main__":
    unittest.main()
