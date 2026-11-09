"""Ghi chú dưới báo cáo (snapshot không có ghi chú). File PDF không bao giờ thay đổi.

- Ai xem được báo cáo thì đọc được ghi chú.
- Viết: chủ báo cáo, hoặc người nhận báo cáo qua một nhóm mình đang thuộc.
  Người chỉ nhận cá nhân thì chỉ đọc.
- Tác giả sửa/xóa ghi chú của mình; chủ báo cáo và System Administrator xóa được mọi ghi chú.
- Mất quyền xem báo cáo thì không xem/viết ghi chú nữa; ghi chú cũ vẫn còn.
"""
import sqlite3
from datetime import datetime
from typing import Optional

MAX_LENGTH = 1000


class NoteError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status, self.message = status, message


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def shared_via_group(conn: sqlite3.Connection, report_id: int, user_id: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM shares s WHERE s.item_type = 'report' AND s.item_id = ? AND s.target_type = 'group'"
        " AND s.target_id IN (SELECT group_id FROM group_members WHERE user_id = ?)", (report_id, user_id)).fetchone()
    return row is not None


def get(conn: sqlite3.Connection, note_id: int) -> Optional[dict]:
    row = conn.execute("SELECT n.*, u.name AS author_name, r.owner_id AS report_owner_id FROM notes n"
                       " JOIN users u ON u.id = n.author_id JOIN reports r ON r.id = n.report_id"
                       " WHERE n.id = ?", (note_id,)).fetchone()
    return dict(row) if row else None


def list_for(conn: sqlite3.Connection, report_id: int) -> list[dict]:
    rows = conn.execute("SELECT n.id, n.report_id, n.author_id, u.name AS author_name, n.body, n.created_at,"
                        " n.updated_at FROM notes n JOIN users u ON u.id = n.author_id"
                        " WHERE n.report_id = ? ORDER BY n.created_at, n.id", (report_id,)).fetchall()
    return [dict(r) for r in rows]


def _clean(body: str) -> str:
    body = (body or "").strip()
    if not body:
        raise NoteError(400, "Write something before saving the note.")
    if len(body) > MAX_LENGTH:
        raise NoteError(400, f"A note can be at most {MAX_LENGTH} characters.")
    return body


def create(conn: sqlite3.Connection, report_id: int, author_id: str, body: str) -> dict:
    cur = conn.execute("INSERT INTO notes (report_id, author_id, body, created_at) VALUES (?,?,?,?)",
                       (report_id, author_id, _clean(body), _now()))
    return get(conn, cur.lastrowid)


def update(conn: sqlite3.Connection, note_id: int, body: str) -> dict:
    conn.execute("UPDATE notes SET body = ?, updated_at = ? WHERE id = ?", (_clean(body), _now(), note_id))
    return get(conn, note_id)


def delete(conn: sqlite3.Connection, note_id: int) -> None:
    conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))


def list_all(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT n.id, n.report_id, r.name AS report_name, n.author_id, u.name AS author_name,"
                        " n.body, n.created_at, n.updated_at FROM notes n JOIN users u ON u.id = n.author_id"
                        " JOIN reports r ON r.id = n.report_id ORDER BY n.created_at DESC, n.id DESC").fetchall()
    return [dict(r) for r in rows]
