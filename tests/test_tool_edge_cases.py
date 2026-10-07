"""教务工具的边界与错误路径测试。

现有测试只覆盖了正常路径。这里补齐：数据库缺失、学号不存在、
无课程 / 无工单记录，以及「给不存在的学生建单不得产生无主工单」。
"""

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from setup_academic_database import initialize_academic_database

from customer_support_chat.app.services.tools.academic_warning import (
    analyze_academic_warning,
)
from customer_support_chat.app.services.tools.students import get_student_profile
from customer_support_chat.app.services.tools.tickets import (
    create_academic_ticket,
    search_academic_tickets,
)

UNKNOWN_STUDENT = "99999999"
CLEAN_STUDENT = "20240001"       # GPA 3.62，课程均通过
WARNING_STUDENT = "20230018"     # GPA 2.41，数据结构需补考
SUSPENDED_STUDENT = "20220007"   # 休学，且无选课记录


class ToolEdgeCaseTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self._tmp.name) / "academic.sqlite")
        initialize_academic_database(self.db_path)
        self.missing_db = str(Path(self._tmp.name) / "not_created.sqlite")

    def tearDown(self):
        self._tmp.cleanup()

    def _ticket_count(self, student_id):
        # 同样要用 closing：sqlite3 的 with 不关闭连接，
        # 否则这个辅助函数自己就会把临时数据库文件锁住。
        with closing(sqlite3.connect(self.db_path)) as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM tickets WHERE student_id = ?", (student_id,)
            ).fetchone()[0]

    # --- 数据库缺失 ---

    def test_every_tool_reports_missing_database(self):
        cases = [
            (get_student_profile, {"student_id": CLEAN_STUDENT}),
            (analyze_academic_warning, {"student_id": CLEAN_STUDENT}),
            (search_academic_tickets, {"student_id": CLEAN_STUDENT}),
            (
                create_academic_ticket,
                {
                    "student_id": CLEAN_STUDENT,
                    "category": "请假申请",
                    "title": "病假",
                },
            ),
        ]

        for tool, arguments in cases:
            with self.subTest(tool=tool.name):
                result = tool.invoke({**arguments, "db_path": self.missing_db})
                self.assertIn("未找到教务数据库", result)

    # --- 学号不存在 ---

    def test_profile_reports_unknown_student(self):
        result = get_student_profile.invoke(
            {"student_id": UNKNOWN_STUDENT, "db_path": self.db_path}
        )

        self.assertIn(f"没有找到学号为 {UNKNOWN_STUDENT}", result)

    def test_warning_reports_unknown_student(self):
        result = analyze_academic_warning.invoke(
            {"student_id": UNKNOWN_STUDENT, "db_path": self.db_path}
        )

        self.assertIn(f"没有找到学号为 {UNKNOWN_STUDENT}", result)

    # --- 记录为空 ---

    def test_student_without_enrollments_shows_placeholder(self):
        result = get_student_profile.invoke(
            {"student_id": SUSPENDED_STUDENT, "db_path": self.db_path}
        )

        self.assertIn("暂无课程记录", result)

    def test_student_without_tickets_is_reported(self):
        result = search_academic_tickets.invoke(
            {"student_id": SUSPENDED_STUDENT, "db_path": self.db_path}
        )

        self.assertIn("暂无教务工单", result)

    # --- 学业预警分支 ---

    def test_clean_student_has_no_risks(self):
        result = analyze_academic_warning.invoke(
            {"student_id": CLEAN_STUDENT, "db_path": self.db_path}
        )

        self.assertIn("当前未发现明显挂科或低 GPA 风险", result)

    def test_low_gpa_student_is_flagged(self):
        result = analyze_academic_warning.invoke(
            {"student_id": WARNING_STUDENT, "db_path": self.db_path}
        )

        self.assertIn("低于 2.5", result)
        self.assertIn("数据结构", result)

    def test_suspended_student_is_flagged_for_enrollment_status(self):
        result = analyze_academic_warning.invoke(
            {"student_id": SUSPENDED_STUDENT, "db_path": self.db_path}
        )

        self.assertIn("休学", result)
        self.assertIn("学籍状态", result)

    # --- 工单 ---

    def test_no_orphan_ticket_is_created_for_unknown_student(self):
        """校验学生存在这道防线必须真的拦住写入，而不只是返回一句提示。"""
        before = self._ticket_count(UNKNOWN_STUDENT)

        result = create_academic_ticket.invoke(
            {
                "student_id": UNKNOWN_STUDENT,
                "category": "请假申请",
                "title": "不存在学生的请假",
                "db_path": self.db_path,
            }
        )

        self.assertIn("无法创建工单", result)
        self.assertEqual(self._ticket_count(UNKNOWN_STUDENT), before)
        self.assertEqual(before, 0)

    def test_created_ticket_is_found_by_search(self):
        created = create_academic_ticket.invoke(
            {
                "student_id": CLEAN_STUDENT,
                "category": "缓考申请",
                "title": "机器学习缓考",
                "db_path": self.db_path,
            }
        )
        self.assertIn("工单创建成功", created)

        searched = search_academic_tickets.invoke(
            {"student_id": CLEAN_STUDENT, "db_path": self.db_path}
        )

        self.assertIn("缓考申请", searched)
        self.assertIn("机器学习缓考", searched)


if __name__ == "__main__":
    unittest.main()
