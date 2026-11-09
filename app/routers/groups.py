"""Nhóm: tạo, đổi tên, xóa, thêm/xóa thành viên, rời nhóm, chuyển quyền chủ nhóm."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import auth, db, groups

router = APIRouter(prefix="/api/groups", tags=["groups"])


class NameBody(BaseModel):
    name: str = ""


class UserBody(BaseModel):
    user_id: str


def _group(conn, user: dict, group_id: str, action: str) -> dict:
    g = groups.get(conn, group_id)
    auth.require(user, action, g)
    return g


def _run(fn):
    try:
        return fn()
    except groups.GroupError as e:
        raise HTTPException(e.status, e.message)


@router.get("")
def my_groups(user: dict = Depends(auth.current_user)):
    with db.get_conn() as conn:
        return groups.list_for(conn, user["id"])


@router.post("")
def create(body: NameBody, user: dict = Depends(auth.current_user)):
    with db.get_conn() as conn:
        return _run(lambda: groups.create(conn, user, body.name))


@router.get("/{group_id}")
def view(group_id: str, user: dict = Depends(auth.current_user)):
    with db.get_conn() as conn:
        g = _group(conn, user, group_id, "view_group")
    g["can_manage"] = auth.can(user, "manage_group", g)
    g["is_member"] = user["id"] in g["member_ids"]
    return g


@router.put("/{group_id}")
def rename(group_id: str, body: NameBody, user: dict = Depends(auth.current_user)):
    with db.get_conn() as conn:
        _group(conn, user, group_id, "manage_group")
        return _run(lambda: groups.rename(conn, user, group_id, body.name))


@router.delete("/{group_id}")
def delete(group_id: str, user: dict = Depends(auth.current_user)):
    with db.get_conn() as conn:
        _group(conn, user, group_id, "manage_group")
        groups.delete(conn, user, group_id)
    return {"ok": True}


@router.get("/{group_id}/candidates")
def candidates(group_id: str, q: str = "", user: dict = Depends(auth.current_user)):
    """Tìm người dùng theo tên hoặc email để thêm vào nhóm."""
    with db.get_conn() as conn:
        _group(conn, user, group_id, "manage_group")
        return groups.search_users(conn, group_id, q)


@router.post("/{group_id}/members")
def add_member(group_id: str, body: UserBody, user: dict = Depends(auth.current_user)):
    with db.get_conn() as conn:
        _group(conn, user, group_id, "manage_group")
        return _run(lambda: groups.add_member(conn, user, group_id, body.user_id))


@router.delete("/{group_id}/members/{user_id}")
def remove_member(group_id: str, user_id: str, user: dict = Depends(auth.current_user)):
    with db.get_conn() as conn:
        _group(conn, user, group_id, "manage_group")
        return _run(lambda: groups.remove_member(conn, user, group_id, user_id))


@router.post("/{group_id}/leave")
def leave(group_id: str, user: dict = Depends(auth.current_user)):
    with db.get_conn() as conn:
        _group(conn, user, group_id, "leave_group")
        _run(lambda: groups.leave(conn, user, group_id))
    return {"ok": True}


@router.put("/{group_id}/owner")
def change_owner(group_id: str, body: UserBody, user: dict = Depends(auth.current_user)):
    with db.get_conn() as conn:
        _group(conn, user, group_id, "manage_group")
        return _run(lambda: groups.change_owner(conn, user, group_id, body.user_id,
                                                allow_non_member=user["is_admin"]))
