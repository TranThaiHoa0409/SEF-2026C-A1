"""Danh mục widget và tùy chọn dashboard của từng người (lựa chọn, bố cục, kỳ)."""
import json
import re
import sqlite3
from dataclasses import dataclass

from . import kpi


@dataclass(frozen=True)
class Widget:
    id: str
    kpi: str
    type: str      # summary, chart

    @property
    def name(self) -> str:
        return f"{self.kpi} · {'Summary' if self.type == 'summary' else 'Chart'}"

    @property
    def group(self) -> str:
        return kpi.KPI_BY_NAME[self.kpi].group


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


# Danh mục giống nhau cho mọi người: 8 widget số + 5 widget biểu đồ = 13.
CHART_KPIS = ["Total Sales", "Average Order Value", "Total Revenue", "New Customers", "Active Users"]
CATALOGUE: list[Widget] = (
    [Widget(f"{_slug(n)}.summary", n, "summary") for n in kpi.KPI_NAMES]
    + [Widget(f"{_slug(n)}.chart", n, "chart") for n in CHART_KPIS]
)
# Sắp theo nhóm Sales, Revenue, Customers, App usage rồi theo thứ tự KPI.
_GROUP_ORDER = ["Sales", "Revenue", "Customers", "App usage"]
CATALOGUE.sort(key=lambda w: (_GROUP_ORDER.index(w.group), kpi.KPI_NAMES.index(w.kpi), w.type != "summary"))
WIDGETS = {w.id: w for w in CATALOGUE}

DEFAULT_WIDGETS = ["total_revenue.summary", "total_sales.summary",
                   "new_customers.summary", "active_users.summary"]
DEFAULT_PERIOD = "last_7_days"
PERIOD_KEYS = kpi.DASHBOARD_PERIODS


# ------------------------------------------------------------------ tùy chọn

def get_prefs(conn: sqlite3.Connection, user_id: str) -> dict:
    """Tùy chọn đã lưu; người mới nhận bộ mặc định."""
    row = conn.execute("SELECT widget_ids_json, period_key FROM dashboard_prefs WHERE user_id = ?",
                       (user_id,)).fetchone()
    if row is None:
        return {"widget_ids": list(DEFAULT_WIDGETS), "period_key": DEFAULT_PERIOD}
    return {"widget_ids": json.loads(row["widget_ids_json"]), "period_key": row["period_key"]}


def _save(conn: sqlite3.Connection, user_id: str, prefs: dict) -> dict:
    conn.execute(
        "INSERT INTO dashboard_prefs (user_id, widget_ids_json, period_key) VALUES (?,?,?)"
        " ON CONFLICT(user_id) DO UPDATE SET widget_ids_json = excluded.widget_ids_json,"
        " period_key = excluded.period_key",
        (user_id, json.dumps(prefs["widget_ids"]), prefs["period_key"]),
    )
    return prefs


def _check_ids(ids: list[str]) -> None:
    unknown = [i for i in ids if i not in WIDGETS]
    if unknown:
        raise ValueError(f"Unknown widget(s): {', '.join(unknown)}")
    if len(set(ids)) != len(ids):
        raise ValueError("The same widget cannot be added twice.")


def save_selection(conn: sqlite3.Connection, user_id: str, widget_ids: list[str]) -> dict:
    """Lưu lựa chọn khi bấm Save. Widget còn giữ thì giữ vị trí, widget mới thêm vào cuối."""
    _check_ids(widget_ids)
    if not widget_ids:
        raise ValueError("Choose at least one widget.")
    prefs = get_prefs(conn, user_id)
    chosen = set(widget_ids)
    kept = [w for w in prefs["widget_ids"] if w in chosen]
    added = [w for w in widget_ids if w not in kept]
    prefs["widget_ids"] = kept + added
    return _save(conn, user_id, prefs)


def save_layout(conn: sqlite3.Connection, user_id: str, widget_ids: list[str]) -> dict:
    """Lưu thứ tự mới sau mỗi lần kéo thả; phải đúng các widget đang có."""
    _check_ids(widget_ids)
    prefs = get_prefs(conn, user_id)
    if sorted(widget_ids) != sorted(prefs["widget_ids"]):
        raise ValueError("The layout must contain exactly the widgets on your dashboard.")
    prefs["widget_ids"] = widget_ids
    return _save(conn, user_id, prefs)


def reset_selection(conn: sqlite3.Connection, user_id: str) -> dict:
    prefs = get_prefs(conn, user_id)
    prefs["widget_ids"] = list(DEFAULT_WIDGETS)
    return _save(conn, user_id, prefs)


def reset_layout(conn: sqlite3.Connection, user_id: str) -> dict:
    """Về thứ tự mặc định (thứ tự trong danh mục), giữ nguyên các widget đang chọn."""
    prefs = get_prefs(conn, user_id)
    order = {w.id: i for i, w in enumerate(CATALOGUE)}
    prefs["widget_ids"] = sorted(prefs["widget_ids"], key=lambda w: order.get(w, len(order)))
    return _save(conn, user_id, prefs)


def save_period(conn: sqlite3.Connection, user_id: str, period_key: str) -> dict:
    if period_key not in PERIOD_KEYS:
        raise ValueError(f"Unknown period '{period_key}'")
    prefs = get_prefs(conn, user_id)
    prefs["period_key"] = period_key
    return _save(conn, user_id, prefs)


# ------------------------------------------------------------------ dữ liệu widget

def widget_data(conn: sqlite3.Connection, widget: Widget, period: kpi.Period) -> dict:
    base = {"id": widget.id, "name": widget.name, "kpi": widget.kpi, "type": widget.type,
            "group": widget.group, "unit": kpi.KPI_BY_NAME[widget.kpi].unit}
    if widget.type == "summary":
        r = kpi.compute(conn, widget.kpi, period)
        return base | {"value": r.value, "status": r.status, "message": r.message, "details": r.details}
    s = kpi.series(conn, widget.kpi, period)
    return base | {"status": s["status"], "message": s["message"], "granularity": s["granularity"],
                   "points": s["points"]}


def build(conn: sqlite3.Connection, user_id: str) -> dict:
    """Toàn bộ dữ liệu dashboard của một người theo tùy chọn đã lưu."""
    prefs = get_prefs(conn, user_id)
    period = kpi.resolve_period(prefs["period_key"])
    widgets, skipped = [], []
    for wid in prefs["widget_ids"]:
        w = WIDGETS.get(wid)
        if w is None:
            skipped.append(f"A widget on your dashboard ({wid}) is no longer available and was skipped.")
            continue
        widgets.append(widget_data(conn, w, period))
    return {"period": period.to_dict(), "widgets": widgets, "skipped": skipped}


def catalogue(conn: sqlite3.Connection, user_id: str) -> dict:
    """Danh mục cho mọi người, đánh dấu widget đã thêm và widget không có dữ liệu trong kỳ đang chọn."""
    prefs = get_prefs(conn, user_id)
    period = kpi.resolve_period(prefs["period_key"])
    added = set(prefs["widget_ids"])
    no_data = {name: kpi.compute(conn, name, period).status == "no_data" for name in kpi.KPI_NAMES}
    items = [{"id": w.id, "name": w.name, "kpi": w.kpi, "type": w.type, "group": w.group,
              "added": w.id in added, "no_data": no_data[w.kpi]} for w in CATALOGUE]
    return {"period": period.to_dict(), "groups": _GROUP_ORDER, "widgets": items}


def default_snapshot_name(period_label: str) -> str:
    return f"Dashboard, {period_label}"
