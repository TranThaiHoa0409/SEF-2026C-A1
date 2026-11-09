"""Nhóm và vai trò trong nhóm (Group Owner, Member).

- Người tạo nhóm thành Group Owner. Thêm thành viên ngay, không cần lời mời.
- Nhóm luôn có đúng một Group Owner; muốn rời thì phải chuyển quyền hoặc xóa nhóm.
- Xóa nhóm: báo cáo và snapshot không bị xóa, chỉ mất chia sẻ cho nhóm đó.
- Thêm/xóa thành viên được ghi vào activity log.
"""
import sqlite3
from datetime import datetime
from typing import Optional

OWNER, MEMBER = "Group Owner", "Member"


class GroupError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status, self.message = status, message


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(conn: sqlite3.Connection, actor_id: str, action: str, target: str) -> None:
    conn.execute("INSERT INTO activity_log (actor_id, action, target, created_at) VALUES (?,?,?,?)",
                 (actor_id, action, target, _now()))


def _name(conn: sqlite3.Connection, user_id: str) -> str:
    row = conn.execute("SELECT name FROM users WHERE id = ?", (user_id,)).fetchone()
    return row["name"] if row else user_id


def get(conn: sqlite3.Connection, group_id: str) -> Optional[dict]:
    row = conn.execute("SELECT g.group_id, g.name, g.owner_id, u.name AS owner_name FROM groups g"
                       " JOIN users u ON u.id = g.owner_id WHERE g.group_id = ?", (group_id,)).fetchone()
    if row is None:
        return None
    d = dict(row)
    d["members"] = [dict(m) for m in conn.execute(
        "SELECT m.user_id, u.name, u.email, m.role, u.is_active FROM group_members m JOIN users u ON u.id = m.user_id"
        " WHERE m.group_id = ? ORDER BY m.role = 'Group Owner' DESC, u.name", (group_id,))]
    d["member_ids"] = [m["user_id"] for m in d["members"]]
    return d


def list_for(conn: sqlite3.Connection, user_id: str) -> list[dict]:
    rows = conn.execute("SELECT g.group_id FROM groups g JOIN group_members m ON m.group_id = g.group_id"
                        " WHERE m.user_id = ? ORDER BY g.name", (user_id,)).fetchall()
    return [get(conn, r[0]) for r in rows]


def list_all(conn: sqlite3.Connection) -> list[dict]:
    return [get(conn, r[0]) for r in conn.execute("SELECT group_id FROM groups ORDER BY name")]


def _clean_name(name: str) -> str:
    name = (name or "").strip()
    if not name:
        raise GroupError(400, "Enter a group name.")
    if len(name) > 60:
        raise GroupError(400, "The group name can be at most 60 characters.")
    return name


def create(conn: sqlite3.Connection, user: dict, name: str) -> dict:
    name = _clean_name(name)
    n = conn.execute("SELECT COALESCE(MAX(CAST(SUBSTR(group_id, 2) AS INTEGER)), 0) FROM groups").fetchone()[0]
    gid = f"G{n + 1:02d}"
    conn.execute("INSERT INTO groups (group_id, name, owner_id) VALUES (?,?,?)", (gid, name, user["id"]))
    conn.execute("INSERT INTO group_members VALUES (?,?,?)", (gid, user["id"], OWNER))
    log(conn, user["id"], "group_created", f"{name} ({gid})")
    return get(conn, gid)


def rename(conn: sqlite3.Connection, actor: dict, group_id: str, name: str) -> dict:
    name = _clean_name(name)
    old = get(conn, group_id)["name"]
    conn.execute("UPDATE groups SET name = ? WHERE group_id = ?", (name, group_id))
    log(conn, actor["id"], "group_renamed", f"{old} -> {name} ({group_id})")
    return get(conn, group_id)


def delete(conn: sqlite3.Connection, actor: dict, group_id: str) -> None:
    g = get(conn, group_id)
    conn.execute("DELETE FROM shares WHERE target_type = 'group' AND target_id = ?", (group_id,))
    conn.execute("DELETE FROM group_members WHERE group_id = ?", (group_id,))
    conn.execute("DELETE FROM groups WHERE group_id = ?", (group_id,))
    log(conn, actor["id"], "group_deleted", f"{g['name']} ({group_id})")


def search_users(conn: sqlite3.Connection, group_id: str, query: str) -> list[dict]:
    """Người dùng đang hoạt động, chưa trong nhóm, tìm theo tên hoặc email."""
    q = f"%{(query or '').strip().lower()}%"
    rows = conn.execute(
        "SELECT id, name, email FROM users WHERE is_active = 1 AND system_role != 'System Administrator'"
        " AND (LOWER(name) LIKE ? OR LOWER(COALESCE(email, '')) LIKE ?)"
        " AND id NOT IN (SELECT user_id FROM group_members WHERE group_id = ?) ORDER BY name LIMIT 20",
        (q, q, group_id)).fetchall()
    return [dict(r) for r in rows]


def add_member(conn: sqlite3.Connection, actor: dict, group_id: str, user_id: str) -> dict:
    user = conn.execute("SELECT id, name, is_active FROM users WHERE id = ?", (user_id,)).fetchone()
    if user is None or not user["is_active"]:
        raise GroupError(400, "Choose an active user.")
    if user_id in get(conn, group_id)["member_ids"]:
        raise GroupError(400, f"{user['name']} is already in this group.")
    conn.execute("INSERT INTO group_members VALUES (?,?,?)", (group_id, user_id, MEMBER))
    log(conn, actor["id"], "member_added", f"{user['name']} to {get(conn, group_id)['name']} ({group_id})")
    return get(conn, group_id)


def remove_member(conn: sqlite3.Connection, actor: dict, group_id: str, user_id: str) -> dict:
    g = get(conn, group_id)
    if user_id not in g["member_ids"]:
        raise GroupError(400, "This user is not in the group.")
    if user_id == g["owner_id"]:
        raise GroupError(400, "The Group Owner cannot be removed. Change the owner first.")
    conn.execute("DELETE FROM group_members WHERE group_id = ? AND user_id = ?", (group_id, user_id))
    action = "member_left" if actor["id"] == user_id else "member_removed"
    log(conn, actor["id"], action, f"{_name(conn, user_id)} from {g['name']} ({group_id})")
    return get(conn, group_id)


def leave(conn: sqlite3.Connection, user: dict, group_id: str) -> None:
    g = get(conn, group_id)
    if user["id"] == g["owner_id"]:
        raise GroupError(400, "You are the Group Owner. Hand the group to another member or delete the group first.")
    remove_member(conn, user, group_id, user["id"])


def change_owner(conn: sqlite3.Connection, actor: dict, group_id: str, new_owner_id: str,
                 allow_non_member: bool = False) -> dict:
    """Chuyển quyền chủ nhóm. Admin được chọn người ngoài nhóm (người đó được thêm vào nhóm)."""
    g = get(conn, group_id)
    user = conn.execute("SELECT id, name, is_active FROM users WHERE id = ?", (new_owner_id,)).fetchone()
    if user is None or not user["is_active"]:
        raise GroupError(400, "Choose an active user as the new Group Owner.")
    if new_owner_id == g["owner_id"]:
        raise GroupError(400, f"{user['name']} is already the Group Owner.")
    if new_owner_id not in g["member_ids"]:
        if not allow_non_member:
            raise GroupError(400, "The new Group Owner must be a member of the group.")
        conn.execute("INSERT INTO group_members VALUES (?,?,?)", (group_id, new_owner_id, MEMBER))
        log(conn, actor["id"], "member_added", f"{user['name']} to {g['name']} ({group_id})")
    conn.execute("UPDATE group_members SET role = ? WHERE group_id = ? AND user_id = ?", (MEMBER, group_id, g["owner_id"]))
    conn.execute("UPDATE group_members SET role = ? WHERE group_id = ? AND user_id = ?", (OWNER, group_id, new_owner_id))
    conn.execute("UPDATE groups SET owner_id = ? WHERE group_id = ?", (new_owner_id, group_id))
    log(conn, actor["id"], "owner_changed", f"{g['name']} ({group_id}): {g['owner_name']} -> {user['name']}")
    return get(conn, group_id)
