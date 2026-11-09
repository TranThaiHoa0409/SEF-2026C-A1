"""Analytics: trend, so sánh hai kỳ, bộ lọc, drill-down."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import analytics, auth, db, kpi

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _filter(text: Optional[str]) -> Optional[kpi.Filter]:
    try:
        return kpi.parse_filter(text)
    except ValueError as e:
        raise HTTPException(400, str(e))


def _filter_dict(flt: Optional[kpi.Filter]) -> Optional[dict]:
    return {"column": flt.column, "value": flt.value, "label": flt.label} if flt else None


@router.get("/filters")
def filters(user: dict = Depends(auth.current_user)):
    with db.get_conn() as conn:
        return {"categories": kpi.filter_values(conn)}


@router.get("/trend")
def trend(kpi_name: str = Query(alias="kpi"), period: str = "last_7_days", filter: Optional[str] = None,
          user: dict = Depends(auth.current_user)):
    if period not in kpi.TREND_PERIODS:
        raise HTTPException(400, f"Unknown period '{period}'")
    if kpi_name not in kpi.SERIES_KPIS:
        raise HTTPException(400, f"Choose one of: {', '.join(kpi.SERIES_KPIS)}")
    flt = _filter(filter)
    p = kpi.resolve_period(period)
    with db.get_conn() as conn:
        s = kpi.series(conn, kpi_name, p, flt)
        total = kpi.compute(conn, kpi_name, p, flt)
    return s | {"period": p.to_dict(), "filter": _filter_dict(flt), "total": total.value,
                "kpis": kpi.SERIES_KPIS, "periods": [{"key": k, "label": kpi.PERIOD_LABELS[k]}
                                                     for k in kpi.TREND_PERIODS]}


@router.get("/compare")
def compare(length: int, a_start: date, b_start: date, filter: Optional[str] = None,
            user: dict = Depends(auth.current_user)):
    flt = _filter(filter)
    try:
        a, b = analytics.compare_periods(length, a_start, b_start)
    except ValueError as e:
        raise HTTPException(400, str(e))
    with db.get_conn() as conn:
        result = analytics.compare(conn, a, b, flt)
    return result | {"length": length, "filter": _filter_dict(flt)}


@router.get("/drilldown")
def drilldown(start: str, end: str, kpi_name: str = Query(alias="kpi"), filter: Optional[str] = None,
              user: dict = Depends(auth.current_user)):
    flt = _filter(filter)
    try:
        lo, hi = kpi.parse_span(start, end)
        with db.get_conn() as conn:
            out = kpi.records(conn, kpi_name, lo, hi, flt)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return out | {"filter": _filter_dict(flt)}
