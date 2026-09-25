import gc
import tempfile
import unittest
from pathlib import Path

from setup_academic_database import initialize_academic_database
from customer_support_chat.app.services.tools.academic_warning import analyze_academic_warning
from customer_support_chat.app.services.tools.academic_policy import lookup_academic_policy
from customer_support_chat.app.services.tools.students import get_student_profile
from customer_support_chat.app.services.tools.tickets import (
    create_academic_ticket,
    search_academic_tickets,
)


class AcademicToolsTest(unittest.TestCase):
    def test_get_student_profile_returns_core_student_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "academic.sqlite"
            initialize_academic_database(db_path)

            result = get_student_profile.invoke(
                {"student_id": "20240001", "db_path": str(db_path)}
            )
            gc.collect()

        self.assertIn("王小明", result)
        self.assertIn("人工智能", result)
        self.assertIn("在读", result)

    def test_lookup_academic_policy_returns_makeup_exam_deadline(self):
        result = lookup_academic_policy.invoke({"query": "补考申请什么时候截止"})

        self.assertIn("补考", result)
        self.assertIn("开学后两周内", result)

    def test_analyze_academic_warning_reports_low_score_risk(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "academic.sqlite"
            initialize_academic_database(db_path)

            result = analyze_academic_warning.invoke(
                {"student_id": "20230018", "db_path": str(db_path)}
            )
            gc.collect()

        self.assertIn("学业预警", result)
        self.assertIn("数据结构", result)
        self.assertIn("需补考", result)

    def test_ticket_tools_create_and_search_academic_ticket(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "academic.sqlite"
            initialize_academic_database(db_path)

            created = create_academic_ticket.invoke(
                {
                    "student_id": "20240001",
                    "category": "请假申请",
                    "title": "机器学习课程请假",
                    "db_path": str(db_path),
                }
            )
            searched = search_academic_tickets.invoke(
                {"student_id": "20240001", "db_path": str(db_path)}
            )
            gc.collect()

        self.assertIn("工单创建成功", created)
        self.assertIn("请假申请", searched)
        self.assertIn("机器学习课程请假", searched)


if __name__ == "__main__":
    unittest.main()
