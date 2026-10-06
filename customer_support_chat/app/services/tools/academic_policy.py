from pathlib import Path

from langchain_core.tools import tool


POLICY_DIR = Path(__file__).parents[4] / "academic_policy_documents"


def _score_document(query: str, content: str) -> int:
    """用最简单的关键词重合打分，后续可以替换成 Qdrant 向量检索。"""
    keywords = [word for word in query.replace("？", " ").replace("?", " ").split() if word]
    score = 0
    for keyword in keywords:
        if keyword in content:
            score += 2

    # 中文短问句经常没有空格，所以给常见教务词一个额外召回通道。
    for keyword in ["补考", "缓考", "成绩复核", "退课", "选课", "学业预警"]:
        if keyword in query and keyword in content:
            score += 3
    return score


@tool
def lookup_academic_policy(query: str, limit: int = 2) -> str:
    """查询教务政策知识库，回答补考、选课、成绩复核等规则问题。"""
    if not POLICY_DIR.exists():
        return f"未找到教务政策目录：{POLICY_DIR}"

    ranked_documents = []
    for path in POLICY_DIR.glob("*.md"):
        content = path.read_text(encoding="utf-8")
        ranked_documents.append((_score_document(query, content), path.name, content))

    # 分数相同时按文件名排序：否则排名会取决于 glob 的枚举顺序，
    # 同一问题在不同文件系统上可能得到不同文档。
    ranked_documents.sort(key=lambda item: (-item[0], item[1]))
    matched_documents = [item for item in ranked_documents if item[0] > 0][:limit]
    if not matched_documents:
        return "没有检索到相关教务政策，请补充更具体的问题。"

    # 返回短文本，避免工具结果太长影响 Agent 后续推理。
    snippets = []
    for _, filename, content in matched_documents:
        first_lines = [line.strip() for line in content.splitlines() if line.strip()]
        snippet = "\n".join(first_lines[:8])
        snippets.append(f"来源：{filename}\n{snippet}")

    return "教务政策检索结果：\n\n" + "\n\n".join(snippets)
