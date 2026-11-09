"""Ghi chú dưới báo cáo."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import auth, db, groups, notes, reports

router = APIRouter(prefix="/api", tags=["notes"])


class NoteBody(BaseModel):
    body: str = ""


def _report(conn, user: dict, report_id: int) -> dict:
    r = reports.get(conn, report_id)
    auth.require(user, "view_report", r)
    return r


def _note(conn, user: dict, report_id: int, note_id: int, action: str) -> dict:
    n = notes.get(conn, note_id)
    if n is not None and n["report_id"] != report_id:
        n = None
    auth.require(user, action, n)
    return n


@router.get("/reports/{report_id}/notes")
def list_notes(report_id: int, user: dict = Depends(auth.current_user)):
    with db.get_conn() as conn:
        r = _report(conn, user, report_id)
        items = notes.list_for(conn, report_id)
    for n in items:
        n["can_edit"] = n["author_id"] == user["id"]
        n["can_delete"] = user["is_admin"] or user["id"] in (n["author_id"], r["owner_id"])
    return {"can_write": auth.can(user, "write_note", r), "items": items}


@router.post("/reports/{report_id}/notes")
def create(report_id: int, body: NoteBody, user: dict = Depends(auth.current_user)):
    with db.get_conn() as conn:
        r = _report(conn, user, report_id)
        auth.require(user, "write_note", r)
        try:
            return notes.create(conn, report_id, user["id"], body.body)
        except notes.NoteError as e:
            raise HTTPException(e.status, e.message)


@router.put("/reports/{report_id}/notes/{note_id}")
def update(report_id: int, note_id: int, body: NoteBody, user: dict = Depends(auth.current_user)):
    with db.get_conn() as conn:
        _note(conn, user, report_id, note_id, "edit_note")
        try:
            return notes.update(conn, note_id, body.body)
        except notes.NoteError as e:
            raise HTTPException(e.status, e.message)


@router.delete("/reports/{report_id}/notes/{note_id}")
def delete(report_id: int, note_id: int, user: dict = Depends(auth.current_user)):
    with db.get_conn() as conn:
        n = _note(conn, user, report_id, note_id, "delete_note")
        notes.delete(conn, note_id)
        if user["id"] != n["author_id"]:
            groups.log(conn, user["id"], "note_deleted", f"note {note_id} by {n['author_name']} on report {report_id}")
    return {"ok": True}
