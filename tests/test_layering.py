"""分层约束测试：核心包不得反向依赖 Web 层。

历史问题：customer_support_chat/app/services/chat_service.py 曾通过
sys.path 注入 + try/except 的方式导入 web_app 的会话日志模块，
形成 core -> web -> core 的循环依赖，导致核心包无法脱离 Web 层独立使用。
"""

import unittest
from pathlib import Path

CORE_PACKAGE = Path("customer_support_chat")
FORBIDDEN_IMPORTS = ("from web_app", "import web_app")


class LayeringTest(unittest.TestCase):
    def test_core_package_does_not_import_web_layer(self):
        offenders = []

        for path in sorted(CORE_PACKAGE.rglob("*.py")):
            content = path.read_text(encoding="utf-8")
            for lineno, line in enumerate(content.splitlines(), start=1):
                if line.strip().startswith(FORBIDDEN_IMPORTS):
                    offenders.append(f"{path}:{lineno}: {line.strip()}")

        self.assertEqual(
            offenders,
            [],
            "核心层不允许依赖 Web 层，应改为由调用方注入依赖。违规导入："
            + "；".join(offenders),
        )


if __name__ == "__main__":
    unittest.main()
