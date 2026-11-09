"""Trang System Administrator: tài khoản, mọi nhóm, mọi ghi chú, activity log, lịch sử upload.

Sửa nhóm (thành viên, chủ nhóm, xóa) dùng chung API /api/groups; quyền Admin nằm trong auth.can.
"""
from fastapi import APIRouter, Depends, HTTPException

from .. import auth, db, groups, notes

router = APIRouter(prefix="/api/admin", tags=["admin"])


def admin(user: dict = Depends(auth.current_user)) -> dict:
    auth.require(user, "admin")
    return user


@router.get("/users")
def users(user: dict = Depends(admin)):
    return auth.list_accounts()


@router.post("/users/{user_id}/deactivate")
def deactivate(user_id: str, user: dict = Depends(admin)):
    if user_id == user["id"]:
        raise HTTPException(400, "You cannot deactivate your own account.")
    with db.get_conn() as conn:
        target = conn.execute("SELECT name, is_active FROM users WHERE id = ?", (user_id,)).fetchone()
        if target is None:
            raise HTTPException(404, "Account not found.")
        if not target["is_active"]:
            raise HTTPException(400, f"{target['name']} is already deactivated.")
        conn.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user_id,))
        conn.execute("DELETE FROM auth_sessions WHERE user_id = ?", (user_id,))   # đăng xuất ngay
        groups.log(conn, user["id"], "user_deactivated", target["name"])
    return {"ok": True}


@router.get("/groups")
def all_groups(user: dict = Depends(admin)):
    with db.get_conn() as conn:
        return groups.list_all(conn)


@router.get("/notes")
def all_notes(user: dict = Depends(admin)):
    with db.get_conn() as conn:
        return notes.list_all(conn)


@router.get("/activity")
def activity(user: dict = Depends(admin)):
    with db.get_conn() as conn:
        rows = conn.execute("SELECT a.*, COALESCE(u.name, a.actor_id) AS actor_name FROM activity_log a"
                            " LEFT JOIN users u ON u.id = a.actor_id ORDER BY a.id DESC LIMIT 200").fetchall()
    return [dict(r) for r in rows]
