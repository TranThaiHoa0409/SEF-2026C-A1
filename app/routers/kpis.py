"""GET /api/kpis: giá trị 8 KPI cho một kỳ và một bộ lọc."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from .. import auth, db, kpi, scheduler

router = APIRouter(prefix="/api", tags=["kpis"])


def period_from_query(period: Optional[str], start: Optional[date], end: Optional[date]) -> kpi.Period:
    """period=last_7_days, hoặc start/end cho một khoảng ngày cụ thể."""
    try:
        if start or end:
            if not (start and end):
                raise ValueError("Give both start and end dates.")
            return kpi.custom_period(start, end)
        return kpi.resolve_period(period or "last_7_days")
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/kpis")
def get_kpis(period: Optional[str] = None, start: Optional[date] = None, end: Optional[date] = None,
             filter: Optional[str] = None, user: dict = Depends(auth.current_user)):
    p = period_from_query(period, start, end)
    try:
        flt = kpi.parse_filter(filter)
    except ValueError as e:
        raise HTTPException(400, str(e))
    with db.get_conn() as conn:
        results = kpi.compute_all(conn, p, flt)
    return {
        "period": p.to_dict(),
        "filter": {"column": flt.column, "value": flt.value, "label": flt.label} if flt else None,
        "kpis": [r.to_dict() for r in results],
        "last_refresh": scheduler.last_refresh(),
    }
