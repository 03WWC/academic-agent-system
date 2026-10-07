import sqlite3
from contextlib import closing
from pathlib import Path

from langchain_core.tools import tool


DEFAULT_DB_PATH = Path(__file__).parents[3] / "data" / "academic.sqlite"


@tool
def analyze_academic_warning(student_id: str, db_path: str = str(DEFAULT_DB_PATH)) -> str:
    """分析学生课程成绩和学籍状态，输出学业预警建议。"""
    db_file = Path(db_path)
    if not db_file.exists():
        return f"未找到教务数据库：{db_file}"

    # 必须用 closing：sqlite3 的 with 只负责提交/回滚事务，并不会关闭连接，
    # 漏掉会让文件句柄一直挂着（Windows 下连数据库文件都删不掉）。
    with closing(sqlite3.connect(db_file)) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 学业预警必须先确认学生身份和整体 GPA。
        cursor.execute(
            """
            SELECT student_id, name, major, enrollment_status, gpa, advisor
            FROM students
            WHERE student_id = ?
            """,
            (student_id,),
        )
        student = cursor.fetchone()
        if not student:
            return f"没有找到学号为 {student_id} 的学生档案。"

        # 课程成绩和修读状态是判断补考、挂科风险的核心依据。
        cursor.execute(
            """
            SELECT c.course_name, c.semester, e.score, e.status
            FROM enrollments e
            JOIN courses c ON c.course_id = e.course_id
            WHERE e.student_id = ?
            ORDER BY c.semester DESC, c.course_name
            """,
            (student_id,),
        )
        enrollments = [dict(row) for row in cursor.fetchall()]
        cursor.close()

    risks = []
    for item in enrollments:
        score = item["score"]
        status = item["status"]
        if status in {"需补考", "未通过", "挂科"} or (score is not None and score < 60):
            risks.append(f"- {item['course_name']}：{score if score is not None else '暂无成绩'}，状态：{status}")

    student_data = dict(student)
    if student_data["gpa"] < 2.5:
        risks.append(f"- GPA 当前为 {student_data['gpa']}，低于 2.5，建议尽快联系导师。")

    if student_data["enrollment_status"] != "在读":
        risks.append(f"- 学籍状态为 {student_data['enrollment_status']}，需要关注复学、注册或学籍异动要求。")

    if not risks:
        return (
            "学业预警分析：\n"
            f"- 学生：{student_data['name']}（{student_data['student_id']}）\n"
            "- 当前未发现明显挂科或低 GPA 风险。\n"
            f"- 建议继续保持学习节奏，如有选课或成绩疑问可联系导师：{student_data['advisor']}。"
        )

    return (
        "学业预警分析：\n"
        f"- 学生：{student_data['name']}（{student_data['student_id']}）\n"
        f"- 专业：{student_data['major']}\n"
        f"- 导师：{student_data['advisor']}\n"
        "风险项：\n"
        + "\n".join(risks)
        + "\n建议：优先确认补考/重修政策，准备必要材料，并尽快联系导师或教务老师。"
    )
