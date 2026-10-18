"""数据库路径配置的测试。

SQLITE_DB_PATH 此前只是 settings.py 里的一个字段，没有任何代码读取它：
三个教务工具各自用 Path(__file__).parents[3] 硬编码默认库路径，于是
README、.env.example、docker-compose.yml 里让人设置的 SQLITE_DB_PATH
完全不起作用（docker-compose 就算改了路径也仍读默认库）。

现在默认值统一来自 settings.SQLITE_DB_PATH，并支持同名环境变量覆盖。
"""

import os
import subprocess
import sys
import unittest
from pathlib import Path

from customer_support_chat.app.core import settings
from customer_support_chat.app.services.tools import academic_warning, students, tickets

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 在模块导入时取一次，避免受环境中其他测试的影响。
_DEFAULT_AT_IMPORT = Path(settings.get_settings().SQLITE_DB_PATH).expanduser()


class DefaultDbPathTest(unittest.TestCase):
    def test_default_is_absolute_and_inside_the_package(self):
        path = students.DEFAULT_DB_PATH

        self.assertTrue(path.is_absolute())
        self.assertEqual(path.name, "academic.sqlite")
        self.assertEqual(path.parent.name, "data")
        self.assertEqual(path.parent.parent.name, "customer_support_chat")

    def test_all_db_tools_share_the_same_default(self):
        """三个工具必须用同一个默认库，不能各写各的硬编码路径。"""
        self.assertEqual(students.DEFAULT_DB_PATH, tickets.DEFAULT_DB_PATH)
        self.assertEqual(students.DEFAULT_DB_PATH, academic_warning.DEFAULT_DB_PATH)

    def test_default_comes_from_settings(self):
        self.assertEqual(students.DEFAULT_DB_PATH, _DEFAULT_AT_IMPORT)


class DbPathEnvOverrideTest(unittest.TestCase):
    def test_tool_default_follows_sqlite_db_path_env(self):
        """设置 SQLITE_DB_PATH 后，工具的默认库路径必须跟着变。

        用子进程而不是 importlib.reload：reload 会替换工具对象，可能干扰
        同进程里其他测试持有的引用。
        """
        target = Path("custom") / "grading.sqlite"
        code = (
            "from customer_support_chat.app.services.tools.students import DEFAULT_DB_PATH\n"
            "print(DEFAULT_DB_PATH)\n"
        )
        env = dict(os.environ)
        env["SQLITE_DB_PATH"] = str(target)

        completed = subprocess.run(
            [sys.executable, "-c", code],
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
        )

        self.assertEqual(
            completed.returncode,
            0,
            msg=f"子进程导入失败：{completed.stderr}",
        )
        self.assertEqual(Path(completed.stdout.strip()), target)


if __name__ == "__main__":
    unittest.main()
