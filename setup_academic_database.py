import sqlite3
from contextlib import closing
from pathlib import Path


DEFAULT_DB_PATH = Path(__file__).parent / "customer_support_chat" / "data" / "academic.sqlite"


def initialize_academic_database(db_path: str | Path = DEFAULT_DB_PATH) -> Path:
    """初始化教务场景 SQLite 数据库，返回实际写入的数据库路径。"""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # 必须用 closing：sqlite3 的 with 只负责提交/回滚事务，并不会关闭连接。
    with closing(sqlite3.connect(db_path)) as conn:
        cursor = conn.cursor()

        # 学生基础档案：Agent 用它回答“我是谁、什么专业、学籍是否正常”。
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                student_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                major TEXT NOT NULL,
                grade TEXT NOT NULL,
                enrollment_status TEXT NOT NULL,
                gpa REAL NOT NULL,
                advisor TEXT NOT NULL
            )
            """
        )

        # 课程表：后续可以扩展成选课推荐、退补选、成绩预警等工具。
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS courses (
                course_id TEXT PRIMARY KEY,
                course_name TEXT NOT NULL,
                teacher TEXT NOT NULL,
                credits INTEGER NOT NULL,
                semester TEXT NOT NULL
            )
            """
        )

        # 学生选课关系：保留成绩和状态，方便做学业风险判断。
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS enrollments (
                student_id TEXT NOT NULL,
                course_id TEXT NOT NULL,
                score REAL,
                status TEXT NOT NULL,
                PRIMARY KEY (student_id, course_id)
            )
            """
        )

        # 工单表：后续接入 human-in-the-loop 审批时可以直接复用。
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id TEXT PRIMARY KEY,
                student_id TEXT NOT NULL,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                status TEXT NOT NULL
            )
            """
        )

        cursor.execute("DELETE FROM enrollments")
        cursor.execute("DELETE FROM tickets")
        cursor.execute("DELETE FROM courses")
        cursor.execute("DELETE FROM students")

        cursor.executemany(
            """
            INSERT INTO students (
                student_id, name, major, grade, enrollment_status, gpa, advisor
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("20240001", "王小明", "人工智能", "2024级", "在读", 3.62, "李老师"),
                ("20230018", "陈雨桐", "软件工程", "2023级", "在读", 2.41, "赵老师"),
                ("20220007", "刘一诺", "数据科学与大数据技术", "2022级", "休学", 3.18, "周老师"),
            ],
        )

        cursor.executemany(
            """
            INSERT INTO courses (
                course_id, course_name, teacher, credits, semester
            ) VALUES (?, ?, ?, ?, ?)
            """,
            [
                ("AI101", "人工智能导论", "张教授", 3, "2026-2027-1"),
                ("CS205", "数据结构", "黄老师", 4, "2026-2027-1"),
                ("ML302", "机器学习工程实践", "孙老师", 3, "2026-2027-1"),
            ],
        )

        cursor.executemany(
            """
            INSERT INTO enrollments (
                student_id, course_id, score, status
            ) VALUES (?, ?, ?, ?)
            """,
            [
                ("20240001", "AI101", 91, "已出分"),
                ("20240001", "CS205", 86, "已出分"),
                ("20230018", "CS205", 58, "需补考"),
                ("20230018", "ML302", None, "修读中"),
            ],
        )

        cursor.executemany(
            """
            INSERT INTO tickets (
                ticket_id, student_id, category, title, status
            ) VALUES (?, ?, ?, ?, ?)
            """,
            [
                ("T-1001", "20230018", "补考申请", "数据结构补考申请", "待提交材料"),
                ("T-1002", "20240001", "成绩复核", "人工智能导论成绩复核", "已关闭"),
            ],
        )

        conn.commit()
        cursor.close()

    return db_path


if __name__ == "__main__":
    path = initialize_academic_database()
    print(f"教务数据库已初始化：{path}")
