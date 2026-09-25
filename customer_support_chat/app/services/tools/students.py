import sqlite3
from pathlib import Path

from langchain_core.tools import tool


DEFAULT_DB_PATH = (
    Path(__file__).parents[3] / "data" / "academic.sqlite"
)


@tool
def get_student_profile(student_id: str, db_path: str = str(DEFAULT_DB_PATH)) -> str:
    """查询学生基础档案和近期课程状态。"""
    db_file = Path(db_path)
    if not db_file.exists():
        return f"未找到教务数据库：{db_file}"

    with sqlite3.connect(db_file) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 先查学生主档案，这是后续所有教务判断的身份基础。
        cursor.execute(
            """
            SELECT student_id, name, major, grade, enrollment_status, gpa, advisor
            FROM students
            WHERE student_id = ?
            """,
            (student_id,),
        )
        student = cursor.fetchone()
        if not student:
            return f"没有找到学号为 {student_id} 的学生档案。"
        student_data = dict(student)

        # 再查课程状态，让 Agent 能顺手回答成绩、补考、修读中的问题。
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

    course_lines = []
    for item in enrollments:
        score = "暂无成绩" if item["score"] is None else f"{item['score']} 分"
        course_lines.append(
            f"- {item['semester']} {item['course_name']}：{score}，状态：{item['status']}"
        )

    courses_text = "\n".join(course_lines) if course_lines else "- 暂无课程记录"

    return (
        f"学生档案：\n"
        f"- 学号：{student_data['student_id']}\n"
        f"- 姓名：{student_data['name']}\n"
        f"- 专业：{student_data['major']}\n"
        f"- 年级：{student_data['grade']}\n"
        f"- 学籍状态：{student_data['enrollment_status']}\n"
        f"- GPA：{student_data['gpa']}\n"
        f"- 导师：{student_data['advisor']}\n"
        f"课程状态：\n{courses_text}"
    )
