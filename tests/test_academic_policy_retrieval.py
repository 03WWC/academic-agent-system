"""教务政策检索的行为测试。

lookup_academic_policy 是课程政策助手唯一的检索入口，
这里固定它的召回、排序、无结果与截断行为。
"""

import unittest
from unittest import mock

from customer_support_chat.app.services.tools import academic_policy


class PolicyRetrievalTest(unittest.TestCase):
    @staticmethod
    def _lookup(query, **kwargs):
        return academic_policy.lookup_academic_policy.invoke({"query": query, **kwargs})

    # --- 召回：不同主题应命中对应文档 ---

    def test_routes_makeup_exam_question_to_its_document(self):
        result = self._lookup("补考申请什么时候截止")

        self.assertIn("makeup_exam_policy.md", result)
        self.assertIn("开学后两周内", result)

    def test_routes_course_selection_question_to_its_document(self):
        result = self._lookup("退课和选课有什么规定")

        self.assertIn("course_selection_policy.md", result)
        self.assertIn("两周内申请退课", result)

    def test_routes_grade_review_question_to_its_document(self):
        result = self._lookup("成绩复核怎么申请")

        self.assertIn("course_selection_policy.md", result)
        self.assertIn("五个工作日", result)

    # --- 无结果 ---

    def test_returns_guidance_when_nothing_matches(self):
        result = self._lookup("火星今天的天气怎么样")

        self.assertIn("没有检索到相关教务政策", result)

    def test_empty_query_matches_nothing(self):
        result = self._lookup("")

        self.assertIn("没有检索到相关教务政策", result)

    # --- 输出结构 ---

    def test_result_labels_every_source(self):
        result = self._lookup("补考 选课", limit=2)

        self.assertEqual(result.count("来源："), 2)
        self.assertIn("makeup_exam_policy.md", result)
        self.assertIn("course_selection_policy.md", result)

    def test_limit_restricts_document_count(self):
        result = self._lookup("补考 选课", limit=1)

        self.assertEqual(result.count("来源："), 1)

    # --- 截断守卫 ---

    def test_policy_documents_fit_within_the_snippet_limit(self):
        """lookup_academic_policy 只返回前 8 个非空行。

        文档一旦超过这个长度，检索结果会静默截断、丢掉后面的内容，
        而调用方（大模型）无从察觉。这里把静默截断变成显式失败：
        真有文档变长时，必须先调整截断策略，而不是让答案悄悄缺一块。
        """
        for path in sorted(academic_policy.POLICY_DIR.glob("*.md")):
            non_empty_lines = [
                line
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            with self.subTest(document=path.name):
                self.assertLessEqual(
                    len(non_empty_lines),
                    8,
                    f"{path.name} 超过 8 个非空行，检索结果会被截断",
                )


class PolicyRankingStabilityTest(unittest.TestCase):
    """同分文档的排序必须稳定，不能取决于文件系统的枚举顺序。

    文档打分相同时（例如「选课 补考」让两份文档都得 5 分），
    谁的排名靠前不应随目录读取顺序变化，否则同一问题会得到不同答案。
    """

    class _StubPolicyDir:
        """固定 glob 的返回顺序，用来模拟不同的文件系统枚举顺序。"""

        def __init__(self, paths):
            self._paths = paths

        def exists(self):
            return True

        def glob(self, pattern):
            return iter(self._paths)

    def _sources(self, names, query, limit=1):
        paths = [academic_policy.POLICY_DIR / name for name in names]
        with mock.patch.object(
            academic_policy, "POLICY_DIR", self._StubPolicyDir(paths)
        ):
            result = academic_policy.lookup_academic_policy.invoke(
                {"query": query, "limit": limit}
            )
        return [line for line in result.splitlines() if line.startswith("来源：")]

    def test_tie_is_broken_independently_of_directory_order(self):
        forward = self._sources(
            ["course_selection_policy.md", "makeup_exam_policy.md"], "选课 补考"
        )
        reversed_order = self._sources(
            ["makeup_exam_policy.md", "course_selection_policy.md"], "选课 补考"
        )

        self.assertEqual(
            forward, reversed_order, "同分文档的排名依赖了目录枚举顺序"
        )


if __name__ == "__main__":
    unittest.main()
