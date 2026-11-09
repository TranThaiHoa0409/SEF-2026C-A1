"""Đăng nhập bằng tài khoản mẫu, phiên 30 phút, và một hàm kiểm tra quyền dùng chung."""
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Cookie, HTTPException

from . import config, db

COOKIE_NAME = "bb_session"
NO_ACCESS = "No access: you do not have permission to view or change this item."
ADMIN_ROLE = "System Administrator"
FMT = "%Y-%m-%d %H:%M:%S"


def now() -> datetime:
    """Giờ thật cho phiên đăng nhập (test thay bằng giờ giả)."""
    return datetime.now()


def list_accounts() -> list[dict]:
    with db.get_conn() as conn:
        rows = conn.execute("SELECT id, name, email, system_role, is_active FROM users ORDER BY id").fetchall()
    return [dict(r) | {"is_active": bool(r["is_active"])} for r in rows]


def login(user_id: str) -> tuple[str, dict]:
    with db.get_conn() as conn:
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if user is None:
            raise HTTPException(404, "Account not found.")
        if not user["is_active"]:
            raise HTTPException(403, "This account has been deactivated and cannot sign in.")
        token = secrets.token_urlsafe(24)
        conn.execute("INSERT INTO auth_sessions VALUES (?,?,?)", (token, user_id, now().strftime(FMT)))
    return token, _user_dict(user)


def logout(token: Optional[str]) -> None:
    if token:
        with db.get_conn() as conn:
            conn.execute("DELETE FROM auth_sessions WHERE token = ?", (token,))


def _user_dict(row) -> dict:
    return {"id": row["id"], "name": row["name"], "email": row["email"],
            "system_role": row["system_role"], "is_admin": row["system_role"] == ADMIN_ROLE}


def current_user(bb_session: Optional[str] = Cookie(default=None)) -> dict:
    """Dependency FastAPI: trả user đang đăng nhập hoặc 401."""
    if not bb_session:
        raise HTTPException(401, "Please sign in.")
    with db.get_conn() as conn:
        row = conn.execute(
            "SELECT s.last_seen, u.* FROM auth_sessions s JOIN users u ON u.id = s.user_id WHERE s.token = ?",
            (bb_session,),
        ).fetchone()
        if row is None:
            raise HTTPException(401, "Please sign in.")
        idle = now() - datetime.strptime(row["last_seen"], FMT)
        if idle > timedelta(minutes=config.SESSION_TIMEOUT_MINUTES) or not row["is_active"]:
            conn.execute("DELETE FROM auth_sessions WHERE token = ?", (bb_session,))
            raise HTTPException(401, "Your session has ended. Please sign in again.")
        conn.execute("UPDATE auth_sessions SET last_seen = ? WHERE token = ?", (now().strftime(FMT), bb_session))
    return _user_dict(row)


# ------------------------------------------------------------------ phân quyền

def is_shared_with(item_type: str, item_id: int, user_id: str) -> bool:
    """Mục được chia sẻ cho người này, trực tiếp hoặc qua một nhóm người này đang thuộc."""
    with db.get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM shares s WHERE s.item_type = ? AND s.item_id = ? AND ("
            " (s.target_type = 'user' AND s.target_id = ?) OR"
            " (s.target_type = 'group' AND s.target_id IN"
            "   (SELECT group_id FROM group_members WHERE user_id = ?)))",
            (item_type, item_id, user_id, user_id),
        ).fetchone()
    return row is not None


def can(user: dict, action: str, item: Optional[dict] = None) -> bool:
    """Một chỗ duy nhất quyết định quyền. Các bước sau thêm action mới vào đây."""
    if action in ("upload_data", "view_upload_history"):
        return user["is_admin"]
    if action == "dev_tools":
        return user["is_admin"]
    if item is None:
        return False
    if action in ("view_snapshot", "view_report"):
        kind = action.removeprefix("view_")
        return item["owner_id"] == user["id"] or is_shared_with(kind, item["id"], user["id"])
    if action in ("delete_snapshot", "share_snapshot", "delete_report", "share_report",
                  "manage_schedule", "manage_rule"):
        key = "user_id" if action == "manage_rule" else "owner_id"
        return item[key] == user["id"]
    return False


def require(user: dict, action: str, item: Optional[dict] = None) -> None:
    """Thiếu quyền thì luôn trả 403 với cùng một thông báo."""
    if not can(user, action, item):
        raise HTTPException(403, NO_ACCESS)
