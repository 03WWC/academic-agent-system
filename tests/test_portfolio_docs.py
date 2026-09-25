import unittest
from pathlib import Path

# 以下文档只保留在本地，未纳入版本管理。
# 文件存在时校验内容，不存在时跳过，保证新克隆的仓库也能通过测试。
# 跳过原因用英文，避免在 Windows GBK 控制台里显示乱码。
PORTFOLIO_DOC = Path("AI_AGENT_PORTFOLIO.md")
RUNBOOK_DOC = Path("PROJECT_RUNBOOK.md")
INTERVIEW_DOC = Path("INTERVIEW_SCRIPT.md")


class PortfolioDocsTest(unittest.TestCase):
    @unittest.skipUnless(PORTFOLIO_DOC.exists(), "AI_AGENT_PORTFOLIO.md is a local-only doc, not tracked")
    def test_portfolio_doc_describes_academic_agent_system(self):
        content = PORTFOLIO_DOC.read_text(encoding="utf-8")

        self.assertIn("教务多 Agent 学生服务系统", content)
        self.assertIn("学生档案助手", content)
        self.assertIn("课程政策助手", content)
        self.assertIn("学业预警助手", content)
        self.assertIn("工单助手", content)
        self.assertIn("简历写法", content)
        self.assertNotIn("航空/旅行", content)
        self.assertNotIn("Flight Assistant", content)
        self.assertNotIn("Hotel Assistant", content)

    @unittest.skipUnless(RUNBOOK_DOC.exists(), "PROJECT_RUNBOOK.md is a local-only doc, not tracked")
    def test_runbook_uses_academic_paths_and_examples(self):
        content = RUNBOOK_DOC.read_text(encoding="utf-8")

        self.assertIn("academic_agent_system", content)
        self.assertIn("http://127.0.0.1:8001/", content)
        self.assertIn("setup_academic_database.py", content)
        self.assertIn("补考申请什么时候截止", content)
        self.assertNotIn("Swiss Airlines", content)
        self.assertNotIn("passenger_id", content)

    @unittest.skipUnless(INTERVIEW_DOC.exists(), "INTERVIEW_SCRIPT.md is a local-only doc, not tracked")
    def test_interview_script_exists(self):
        content = INTERVIEW_DOC.read_text(encoding="utf-8")

        self.assertIn("一分钟讲法", content)
        self.assertIn("项目亮点", content)
        self.assertIn("面试追问", content)


if __name__ == "__main__":
    unittest.main()
