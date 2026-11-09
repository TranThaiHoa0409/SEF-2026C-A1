"""Báo cáo PDF và báo cáo định kỳ."""
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from .. import auth, db, reports, shares

router = APIRouter(prefix="/api", tags=["reports"])


class ReportBody(BaseModel):
    kpis: list[str] = []
    period_key: str = "last_7_days"
    name: Optional[str] = None
    confirm_skip: bool = False


class ScheduleBody(BaseModel):
    kpis: list[str] = []
    period_key: str = "last_7_days"
    frequency: str = "weekly"
    first_run: str = ""
    name: Optional[str] = None
    active: bool = True


def _error(e: reports.ReportError) -> JSONResponse:
    return JSONResponse(status_code=e.status, content={"detail": e.message, **e.extra})


def _report_for(user: dict, report_id: int, action: str) -> dict:
    with db.get_conn() as conn:
        r = reports.get(conn, report_id)
    auth.require(user, action, r)
    return r


@router.post("/reports")
def create(body: ReportBody, user: dict = Depends(auth.current_user)):
    try:
        with db.get_conn() as conn:
            return reports.generate(conn, user, body.kpis, body.period_key, body.name, body.confirm_skip)
    except reports.ReportError as e:
        return _error(e)


@router.get("/reports")
def list_reports(user: dict = Depends(auth.current_user)):
    with db.get_conn() as conn:
        return reports.list_for(conn, user["id"])


@router.get("/reports/{report_id}")
def view(report_id: int, user: dict = Depends(auth.current_user)):
    r = _report_for(user, report_id, "view_report")
    r.pop("pdf_path", None)
    is_owner = r["owner_id"] == user["id"]
    r["is_owner"] = is_owner
    r["can_write_notes"] = auth.can(user, "write_note", r)
    if is_owner:
        with db.get_conn() as conn:
            r["shares"] = shares.list_shares(conn, "report", report_id)
    return r


@router.get("/reports/{report_id}/pdf")
def download(report_id: int, user: dict = Depends(auth.current_user)):
    r = _report_for(user, report_id, "view_report")
    if not r["pdf_path"] or not Path(r["pdf_path"]).exists():
        raise HTTPException(404, "The PDF file is missing.")
    return FileResponse(r["pdf_path"], media_type="application/pdf", filename=f"{r['name']}.pdf")


@router.delete("/reports/{report_id}")
def delete(report_id: int, user: dict = Depends(auth.current_user)):
    _report_for(user, report_id, "delete_report")
    with db.get_conn() as conn:
        reports.delete(conn, report_id)
    return {"ok": True}


# ------------------------------------------------------------------ lịch

def _schedule_for(user: dict, schedule_id: int) -> dict:
    with db.get_conn() as conn:
        s = reports.get_schedule(conn, schedule_id)
    auth.require(user, "manage_schedule", s)
    return s


@router.get("/schedules")
def list_schedules(user: dict = Depends(auth.current_user)):
    with db.get_conn() as conn:
        return reports.list_schedules(conn, user["id"])


@router.post("/schedules")
def create_schedule(body: ScheduleBody, user: dict = Depends(auth.current_user)):
    try:
        with db.get_conn() as conn:
            return reports.create_schedule(conn, user["id"], body.kpis, body.period_key, body.frequency,
                                           body.first_run, body.name)
    except reports.ReportError as e:
        return _error(e)


@router.put("/schedules/{schedule_id}")
def update_schedule(schedule_id: int, body: ScheduleBody, user: dict = Depends(auth.current_user)):
    _schedule_for(user, schedule_id)
    try:
        with db.get_conn() as conn:
            return reports.update_schedule(conn, schedule_id, body.kpis, body.period_key, body.frequency,
                                           body.first_run, body.name, body.active)
    except reports.ReportError as e:
        return _error(e)


@router.delete("/schedules/{schedule_id}")
def delete_schedule(schedule_id: int, user: dict = Depends(auth.current_user)):
    _schedule_for(user, schedule_id)
    with db.get_conn() as conn:
        reports.delete_schedule(conn, schedule_id)
    return {"ok": True}
