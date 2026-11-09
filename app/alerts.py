"""Rule cảnh báo theo ngưỡng và kiểm tra sau mỗi lần refresh.

Mỗi rule xét giá trị KPI của một ngày (mặc định ngày đầy đủ gần nhất, 7 Nov).
Alert chỉ tạo khi KPI vừa cắt ngưỡng; còn đang vượt thì không tạo thêm (is_triggered).
"""
import sqlite3
from datetime import date, timedelta
from typing import Optional

from . import config, kpi, notify

CONDITIONS = ("above", "below")


def fmt_value(value: float, unit: str) -> str:
    if unit == "money":
        return f"${value:,.2f}"
    if unit == "percent":
        return f"{value * 100:.1f}%"
    return f"{value:,.0f}" if float(value).is_integer() else f"{value:,.2f}"


def alert_day() -> date:
    return config.TODAY - timedelta(days=config.ALERT_DAY_OFFSET)


# ------------------------------------------------------------------ rule

def _validate(kpi_name: str, condition: str, threshold) -> float:
    if kpi_name not in kpi.KPI_NAMES:
        raise ValueError("Choose a KPI from the list.")
    if condition not in CONDITIONS:
        raise ValueError("Choose a condition: goes above or goes below.")
    if threshold is None or (isinstance(threshold, str) and not threshold.strip()):
        raise ValueError("Enter a threshold number.")
    try:
        value = float(threshold)
    except (TypeError, ValueError):
        raise ValueError("The threshold must be a number.")
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError("The threshold must be a number.")
    return value


def list_rules(conn: sqlite3.Connection, user_id: str) -> list[dict]:
    rows = conn.execute("SELECT * FROM alert_rules WHERE user_id = ? ORDER BY id", (user_id,)).fetchall()
    return [_rule_dict(r) for r in rows]


def get_rule(conn: sqlite3.Connection, rule_id: str) -> Optional[dict]:
    row = conn.execute("SELECT * FROM alert_rules WHERE id = ?", (rule_id,)).fetchone()
    return _rule_dict(row) if row else None


def _rule_dict(r) -> dict:
    unit = kpi.KPI_BY_NAME[r["kpi"]].unit
    return {"id": r["id"], "user_id": r["user_id"], "kpi": r["kpi"], "condition": r["condition"],
            "threshold": r["threshold"], "unit": unit, "is_active": bool(r["is_active"]),
            "is_triggered": bool(r["is_triggered"]),
            "text": f"{r['kpi']} goes {r['condition']} {fmt_value(r['threshold'], unit)}"}


def create_rule(conn: sqlite3.Connection, user_id: str, kpi_name: str, condition: str, threshold) -> dict:
    value = _validate(kpi_name, condition, threshold)
    n = conn.execute("SELECT COALESCE(MAX(CAST(SUBSTR(id, 2) AS INTEGER)), 0) FROM alert_rules").fetchone()[0]
    rule_id = f"R{n + 1:02d}"
    conn.execute("INSERT INTO alert_rules (id, user_id, kpi, condition, threshold, is_active, is_triggered)"
                 " VALUES (?,?,?,?,?,1,0)", (rule_id, user_id, kpi_name, condition, value))
    return get_rule(conn, rule_id)


def update_rule(conn: sqlite3.Connection, rule_id: str, kpi_name: str, condition: str, threshold,
                is_active: bool) -> dict:
    value = _validate(kpi_name, condition, threshold)
    old = get_rule(conn, rule_id)
    changed = (old["kpi"], old["condition"], old["threshold"]) != (kpi_name, condition, value)
    # Sửa rule hoặc tắt rule: coi như rule mới, quên trạng thái đang vượt ngưỡng.
    reset = changed or not is_active
    conn.execute("UPDATE alert_rules SET kpi = ?, condition = ?, threshold = ?, is_active = ?,"
                 " is_triggered = CASE WHEN ? THEN 0 ELSE is_triggered END WHERE id = ?",
                 (kpi_name, condition, value, int(is_active), int(reset), rule_id))
    return get_rule(conn, rule_id)


def delete_rule(conn: sqlite3.Connection, rule_id: str) -> None:
    conn.execute("DELETE FROM alert_rules WHERE id = ?", (rule_id,))


# ------------------------------------------------------------------ kiểm tra

def check_rules(conn: sqlite3.Connection, day: Optional[date] = None) -> list[int]:
    """Kiểm tra mọi rule đang bật với giá trị KPI của một ngày. Trả id các thông báo vừa tạo."""
    day = day or alert_day()
    period = kpi.Period(day, day)
    created = []
    values: dict[str, kpi.KpiResult] = {}
    for r in conn.execute("SELECT * FROM alert_rules WHERE is_active = 1 ORDER BY id").fetchall():
        res = values.get(r["kpi"]) or kpi.compute(conn, r["kpi"], period)
        values[r["kpi"]] = res
        if res.value is None:   # không có dữ liệu: bỏ qua rule, không tạo alert
            continue
        crossed = res.value < r["threshold"] if r["condition"] == "below" else res.value > r["threshold"]
        if crossed and not r["is_triggered"]:
            unit = res.unit
            title = f"{r['kpi']} went {r['condition']} {fmt_value(r['threshold'], unit)}"
            body = (f"{r['kpi']} was {fmt_value(res.value, unit)} on {kpi.format_range(day, day)}, "
                    f"{r['condition']} your threshold of {fmt_value(r['threshold'], unit)} (rule {r['id']}).")
            created.append(notify.notify(
                conn, r["user_id"], "alert", title, body, email_type="alert", link="#/alerts",
                rule_id=r["id"], kpi=r["kpi"], condition=r["condition"], threshold=r["threshold"],
                value=res.value, data_date=day.isoformat()))
            conn.execute("UPDATE alert_rules SET is_triggered = 1 WHERE id = ?", (r["id"],))
        elif not crossed and r["is_triggered"]:
            conn.execute("UPDATE alert_rules SET is_triggered = 0 WHERE id = ?", (r["id"],))
    return created
