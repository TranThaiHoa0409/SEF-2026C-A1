"""Chia sẻ báo cáo và snapshot cho cá nhân và nhóm; thu hồi quyền.

- Chỉ chủ sở hữu được chia sẻ.
- Chia sẻ cho bất kỳ người dùng nào đang hoạt động; cho nhóm thì chỉ nhóm chủ sở hữu đang thuộc.
- Người nhận báo cáo được thông báo trong app và qua email (cùng quy tắc với cảnh báo).
"""
import sqlite3
from datetime import datetime

from . import notify

ITEM_TYPES = ("report", "snapshot")


class ShareError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status, self.message = status, message


def _item(conn: sqlite3.Connection, item_type: str, item_id: int):
    table = "reports" if item_type == "report" else "snapshots"
    return conn.execute(f"SELECT id, owner_id, name FROM {table} WHERE id = ?", (item_id,)).fetchone()


def user_groups(conn: sqlite3.Connection, user_id: str) -> list[dict]:
    rows = conn.execute("SELECT g.group_id, g.name FROM groups g JOIN group_members m ON m.group_id = g.group_id"
                        " WHERE m.user_id = ? ORDER BY g.name", (user_id,)).fetchall()
    return [dict(r) for r in rows]


def targets(conn: sqlite3.Connection, user_id: str) -> dict:
    users = conn.execute("SELECT id, name, email FROM users WHERE is_active = 1 AND id != ? ORDER BY name",
                         (user_id,)).fetchall()
    return {"users": [dict(u) for u in users], "groups": user_groups(conn, user_id)}


def list_shares(conn: sqlite3.Connection, item_type: str, item_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT s.id, s.target_type, s.target_id, s.created_at,"
        " CASE s.target_type WHEN 'user' THEN (SELECT name FROM users WHERE id = s.target_id)"
        " ELSE (SELECT name FROM groups WHERE group_id = s.target_id) END AS target_name"
        " FROM shares s WHERE s.item_type = ? AND s.item_id = ? ORDER BY s.id", (item_type, item_id)).fetchall()
    return [dict(r) for r in rows]


def share(conn: sqlite3.Connection, owner: dict, item_type: str, item_id: int,
          target_type: str, target_id: str) -> dict:
    """owner đã được kiểm tra là chủ sở hữu (auth.require)."""
    item = _item(conn, item_type, item_id)
    if target_type == "user":
        target = conn.execute("SELECT id, name, is_active FROM users WHERE id = ?", (target_id,)).fetchone()
        if target is None or not target["is_active"]:
            raise ShareError(400, "Choose an active user to share with.")
        if target_id == owner["id"]:
            raise ShareError(400, "You already own this item.")
        recipients = [target_id]
        target_name = target["name"]
    elif target_type == "group":
        group = conn.execute("SELECT group_id, name FROM groups WHERE group_id = ?", (target_id,)).fetchone()
        mine = {g["group_id"] for g in user_groups(conn, owner["id"])}
        if group is None or target_id not in mine:
            raise ShareError(403, "No access: you can only share with groups you belong to.")
        recipients = [r[0] for r in conn.execute(
            "SELECT m.user_id FROM group_members m JOIN users u ON u.id = m.user_id"
            " WHERE m.group_id = ? AND m.user_id != ? AND u.is_active = 1", (target_id, owner["id"]))]
        target_name = group["name"]
    else:
        raise ShareError(400, "Share with a user or a group.")

    exists = conn.execute("SELECT 1 FROM shares WHERE item_type = ? AND item_id = ? AND target_type = ?"
                          " AND target_id = ?", (item_type, item_id, target_type, target_id)).fetchone()
    if exists:
        raise ShareError(400, f"This {item_type} is already shared with {target_name}.")

    cur = conn.execute("INSERT INTO shares (item_type, item_id, target_type, target_id, created_at)"
                       " VALUES (?,?,?,?,?)", (item_type, item_id, target_type, target_id,
                                               datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    if item_type == "report":
        via = f" through the group {target_name}" if target_type == "group" else ""
        for uid in recipients:
            notify.notify(conn, uid, "share", f"{owner['name']} shared a report with you",
                          f"{owner['name']} shared the report \"{item['name']}\" with you{via}. "
                          "Open it from Reports, Shared with me.",
                          email_type="share", link=f"#/report/{item_id}")
    return {"id": cur.lastrowid, "target_type": target_type, "target_id": target_id, "target_name": target_name,
            "notified": recipients if item_type == "report" else []}


def revoke(conn: sqlite3.Connection, share_id: int) -> None:
    conn.execute("DELETE FROM shares WHERE id = ?", (share_id,))


def get_share(conn: sqlite3.Connection, share_id: int):
    return conn.execute("SELECT * FROM shares WHERE id = ?", (share_id,)).fetchone()


def owner_of(conn: sqlite3.Connection, item_type: str, item_id: int):
    if item_type not in ITEM_TYPES:
        return None
    row = _item(conn, item_type, item_id)
    return dict(row) if row else None
