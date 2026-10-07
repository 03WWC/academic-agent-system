"""数据库连接必须被显式关闭。

sqlite3 的 with 语句只负责提交/回滚事务，并不会关闭连接。
四个教务工具原先都直接写 with sqlite3.connect(...)，导致连接泄漏：
Windows 下数据库文件句柄残留、连临时文件都删不掉，
长驻的 Web 服务里连接还会持续累积。

这里断言连接真的被关闭，而不是靠文件能否删除来判断
（在 Linux 上删除已打开的文件会成功，那种断言在 CI 里永远抓不到问题）。
"""

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from setup_academic_database import initialize_academic_database

from customer_support_chat.app.services.tools.academic_warning import (
    analyze_academic_warning,
)
from customer_support_chat.app.services.tools.students import get_student_profile
from customer_support_chat.app.services.tools.tickets import (
    create_academic_ticket,
    search_academic_tickets,
)


def _invoke_capturing_connections(tool, arguments):
    """调用工具并收集它打开的每一个数据库连接。"""
    opened = []
    real_connect = sqlite3.connect

    def tracking_connect(*args, **kwargs):
        connection = real_connect(*args, **kwargs)
        opened.append(connection)
        return connection

    with mock.patch.object(sqlite3, "connect", tracking_connect):
        tool.invoke(arguments)

    return opened


def _assert_all_closed(test_case, connections, label):
    test_case.assertTrue(connections, f"{label} 没有连接数据库")
    for connection in connections:
        with test_case.assertRaises(sqlite3.ProgrammingError):
            # 已关闭的连接上执行语句会抛 ProgrammingError
            connection.execute("SELECT 1")


class ToolConnectionTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self._tmp.name) / "academic.sqlite")
        initialize_academic_database(self.db_path)

    def tearDown(self):
        self._tmp.cleanup()

    def test_every_tool_closes_its_connection(self):
        cases = [
            (get_student_profile, {"student_id": "20240001"}),
            (analyze_academic_warning, {"student_id": "20240001"}),
            (search_academic_tickets, {"student_id": "20240001"}),
            (
                create_academic_ticket,
                {
                    "student_id": "20240001",
                    "category": "请假申请",
                    "title": "病假",
                },
            ),
        ]

        for tool, arguments in cases:
            opened = _invoke_capturing_connections(
                tool, {**arguments, "db_path": self.db_path}
            )
            with self.subTest(tool=tool.name):
                _assert_all_closed(self, opened, tool.name)

    def test_tools_close_connection_on_early_return(self):
        """提前返回的分支同样要关闭连接。

        查不到学生时会直接 return，旧代码在那条路径上连 cursor.close() 都跳过了。
        """
        cases = [
            (get_student_profile, {"student_id": "99999999"}),
            (analyze_academic_warning, {"student_id": "99999999"}),
            (
                create_academic_ticket,
                {"student_id": "99999999", "category": "请假申请", "title": "无主工单"},
            ),
        ]

        for tool, arguments in cases:
            opened = _invoke_capturing_connections(
                tool, {**arguments, "db_path": self.db_path}
            )
            with self.subTest(tool=tool.name):
                _assert_all_closed(self, opened, tool.name)

    def test_setup_script_closes_its_connection(self):
        target = str(Path(self._tmp.name) / "second.sqlite")
        opened = []

        real_connect = sqlite3.connect

        def tracking_connect(*args, **kwargs):
            connection = real_connect(*args, **kwargs)
            opened.append(connection)
            return connection

        with mock.patch.object(sqlite3, "connect", tracking_connect):
            initialize_academic_database(target)

        _assert_all_closed(self, opened, "initialize_academic_database")


if __name__ == "__main__":
    unittest.main()
