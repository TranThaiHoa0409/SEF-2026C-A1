"""Dashboard: danh mục widget, lựa chọn, bố cục, kỳ."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import auth, dashboard, db, scheduler

router = APIRouter(prefix="/api", tags=["dashboard"])


class WidgetIds(BaseModel):
    widget_ids: list[str]


class PeriodBody(BaseModel):
    period_key: str


def _run(fn, user: dict, *args):
    try:
        with db.get_conn() as conn:
            return fn(conn, user["id"], *args)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/widgets")
def widgets(user: dict = Depends(auth.current_user)):
    return _run(dashboard.catalogue, user)


@router.get("/dashboard")
def get_dashboard(user: dict = Depends(auth.current_user)):
    data = _run(dashboard.build, user)
    data["last_refresh"] = scheduler.last_refresh()
    return data


@router.put("/dashboard/selection")
def save_selection(body: WidgetIds, user: dict = Depends(auth.current_user)):
    return _run(dashboard.save_selection, user, body.widget_ids)


@router.put("/dashboard/layout")
def save_layout(body: WidgetIds, user: dict = Depends(auth.current_user)):
    return _run(dashboard.save_layout, user, body.widget_ids)


@router.post("/dashboard/reset")
def reset_selection(user: dict = Depends(auth.current_user)):
    return _run(dashboard.reset_selection, user)


@router.post("/dashboard/layout/reset")
def reset_layout(user: dict = Depends(auth.current_user)):
    return _run(dashboard.reset_layout, user)


@router.put("/dashboard/period")
def save_period(body: PeriodBody, user: dict = Depends(auth.current_user)):
    return _run(dashboard.save_period, user, body.period_key)
