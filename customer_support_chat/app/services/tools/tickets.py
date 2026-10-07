import sqlite3
import uuid
from contextlib import closing
from pathlib import Path

from langchain_core.tools import tool


DEFAULT_DB_PATH = Path(__file__).parents[3] / "data" / "academic.sqlite"


@tool
def create_academic_ticket(
    student_id: str,
    category: str,
    title: str,
    db_path: str = str(DEFAULT_DB_PATH),
) -> str:
    """创建教务工单，适用于请假、补考、成绩复核、申诉等申请。"""
    db_file = Path(db_path)
    if not db_file.exists():
        return f"未找到教务数据库：{db_file}"

    ticket_id = f"T-{uuid.uuid4().hex[:8].upper()}"
    # 必须用 closing：sqlite3 的 with 只负责提交/回滚事务，并不会关闭连接，
    # 漏掉会让文件句柄一直挂着（Windows 下连数据库文件都删不掉）。
    with closing(sqlite3.connect(db_file)) as conn:
        cursor = conn.cursor()

        # 创建工单前先校验学生存在，避免产生无主申请。
        cursor.execute("SELECT 1 FROM students WHERE student_id = ?", (student_id,))
        if not cursor.fetchone():
            return f"没有找到学号为 {student_id} 的学生档案，无法创建工单。"

        cursor.execute(
            """
            INSERT INTO tickets (ticket_id, student_id, category, title, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (ticket_id, student_id, category, title, "待处理"),
        )
        conn.commit()
        cursor.close()

    return f"工单创建成功：{ticket_id}，类型：{category}，标题：{title}，状态：待处理。"


@tool
def search_academic_tickets(student_id: str, db_path: str = str(DEFAULT_DB_PATH)) -> str:
    """按学号查询教务工单列表。"""
    db_file = Path(db_path)
    if not db_file.exists():
        return f"未找到教务数据库：{db_file}"

    # 必须用 closing：sqlite3 的 with 只负责提交/回滚事务，并不会关闭连接，
    # 漏掉会让文件句柄一直挂着（Windows 下连数据库文件都删不掉）。
    with closing(sqlite3.connect(db_file)) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT ticket_id, category, title, status
            FROM tickets
            WHERE student_id = ?
            ORDER BY ticket_id DESC
            """,
            (student_id,),
        )
        tickets = [dict(row) for row in cursor.fetchall()]
        cursor.close()

    if not tickets:
        return f"学号 {student_id} 暂无教务工单。"

    lines = [
        f"- {item['ticket_id']}：{item['category']}，{item['title']}，状态：{item['status']}"
        for item in tickets
    ]
    return f"教务工单列表（学号：{student_id}）：\n" + "\n".join(lines)
