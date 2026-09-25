import unittest
from pathlib import Path


class AcademicGraphTest(unittest.TestCase):
    def test_graph_imports_without_legacy_vector_dependencies(self):
        from customer_support_chat.app.graph import multi_agentic_graph

        self.assertIsNotNone(multi_agentic_graph)

    def test_graph_uses_four_specialized_academic_assistants(self):
        graph_source = Path("customer_support_chat/app/graph.py").read_text(encoding="utf-8")

        self.assertIn("student_profile_assistant", graph_source)
        self.assertIn("course_policy_assistant", graph_source)
        self.assertIn("academic_warning_assistant", graph_source)
        self.assertIn("ticket_assistant", graph_source)
        self.assertNotIn("academic_assistant import", graph_source)

    def test_specialized_academic_assistants_can_import(self):
        from customer_support_chat.app.services.assistants.student_profile_assistant import (
            ToStudentProfileAssistant,
            student_profile_assistant,
        )
        from customer_support_chat.app.services.assistants.course_policy_assistant import (
            ToCoursePolicyAssistant,
            course_policy_assistant,
        )
        from customer_support_chat.app.services.assistants.academic_warning_assistant import (
            ToAcademicWarningAssistant,
            academic_warning_assistant,
        )
        from customer_support_chat.app.services.assistants.ticket_assistant import (
            ToTicketAssistant,
            ticket_assistant,
        )

        self.assertEqual(ToStudentProfileAssistant.__name__, "ToStudentProfileAssistant")
        self.assertEqual(ToCoursePolicyAssistant.__name__, "ToCoursePolicyAssistant")
        self.assertEqual(ToAcademicWarningAssistant.__name__, "ToAcademicWarningAssistant")
        self.assertEqual(ToTicketAssistant.__name__, "ToTicketAssistant")
        self.assertIsNotNone(student_profile_assistant)
        self.assertIsNotNone(course_policy_assistant)
        self.assertIsNotNone(academic_warning_assistant)
        self.assertIsNotNone(ticket_assistant)

    def test_runtime_directories_only_keep_academic_modules(self):
        assistant_files = {
            path.name
            for path in Path("customer_support_chat/app/services/assistants").glob("*.py")
        }
        tool_files = {
            path.name for path in Path("customer_support_chat/app/services/tools").glob("*.py")
        }

        self.assertEqual(
            assistant_files,
            {
                "__init__.py",
                "assistant_base.py",
                "primary_assistant.py",
                "student_profile_assistant.py",
                "course_policy_assistant.py",
                "academic_warning_assistant.py",
                "ticket_assistant.py",
            },
        )
        self.assertEqual(
            tool_files,
            {
                "__init__.py",
                "students.py",
                "academic_policy.py",
                "academic_warning.py",
                "tickets.py",
            },
        )

    def test_readme_describes_academic_agent_system(self):
        readme = Path("README.md").read_text(encoding="utf-8")

        self.assertIn("教务多 Agent 学生服务系统", readme)
        self.assertIn("学生档案助手", readme)
        self.assertIn("课程政策助手", readme)
        self.assertIn("学业预警助手", readme)
        self.assertIn("工单助手", readme)


if __name__ == "__main__":
    unittest.main()
