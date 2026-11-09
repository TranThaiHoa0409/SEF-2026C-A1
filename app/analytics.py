"""So sánh hai kỳ cùng độ dài. Mọi giá trị KPI lấy từ app/kpi.py."""
import sqlite3
from datetime import date, timedelta
from typing import Optional

from . import config, kpi

COMPARE_LENGTHS = [1, 7, 30]


def compare_periods(length: int, a_start: date, b_start: date,
                    today: date = config.TODAY) -> tuple[kpi.Period, kpi.Period]:
    """Tạo hai kỳ cùng độ dài từ hai ngày bắt đầu; kiểm tra không trùng và không ở tương lai."""
    if length not in COMPARE_LENGTHS:
        raise ValueError(f"Choose a length of {', '.join(map(str, COMPARE_LENGTHS))} days.")
    a = kpi.Period(a_start, a_start + timedelta(days=length - 1))
    b = kpi.Period(b_start, b_start + timedelta(days=length - 1))
    for name, p in (("Period A", a), ("Period B", b)):
        if p.end > today:
            raise ValueError(f"{name} ends on {p.end.isoformat()}, which is in the future. Choose an earlier start date.")
    if a.start <= b.end and b.start <= a.end:
        raise ValueError("The two periods overlap or are the same. Change the start date of one period.")
    return a, b


def _diff(a: Optional[float], b: Optional[float], unit: str) -> tuple[Optional[float], Optional[float]]:
    if a is None or b is None:
        return None, None
    diff = round(a - b, 2) if unit == "money" else a - b
    pct = (a - b) / b if b else None
    return diff, pct


def compare(conn: sqlite3.Connection, a: kpi.Period, b: kpi.Period, flt: Optional[kpi.Filter] = None) -> dict:
    rows = []
    for name in kpi.KPI_NAMES:
        if name == "Revenue Growth":
            # Revenue Growth của A so với B (README: chênh lệch Total Revenue chính là Revenue Growth).
            r = kpi.compute(conn, name, a, flt, compare_to=b)
            rows.append({"kpi": name, "unit": "percent", "is_growth": True, "value": r.value,
                         "status": r.status, "message": r.message})
            continue
        ra, rb = kpi.compute(conn, name, a, flt), kpi.compute(conn, name, b, flt)
        diff, pct = _diff(ra.value, rb.value, ra.unit)
        rows.append({"kpi": name, "unit": ra.unit, "is_growth": False,
                     "a": ra.value, "a_status": ra.status, "a_message": ra.message,
                     "b": rb.value, "b_status": rb.status, "b_message": rb.message,
                     "difference": diff, "percent": pct})

    def has_data(key: str) -> bool:
        return any(r.get(f"{key}_status") == "ok" for r in rows if not r["is_growth"])

    # Nêu rõ kỳ nào thiếu dữ liệu cho KPI nào; với các KPI đó chỉ hiện kỳ còn lại.
    with_filter = f" with filter {flt.label}" if flt else ""
    notices = []
    for key, other, p, label in (("a", "b", a, "Period A"), ("b", "a", b, "Period B")):
        if not has_data(key):
            notices.append(f"{label} ({p.dates_text}) has no data{with_filter}. Only the other period is shown.")
            continue
        missing = [r["kpi"] for r in rows if not r["is_growth"]
                   and r[f"{key}_status"] == "no_data" and r[f"{other}_status"] == "ok"]
        if missing:
            notices.append(f"{label} ({p.dates_text}) has no data{with_filter} for {', '.join(missing)}. "
                           "Only the other period is shown for these KPIs.")
    return {"a": a.to_dict(), "b": b.to_dict(), "a_has_data": has_data("a"), "b_has_data": has_data("b"),
            "notices": notices, "kpis": rows}
