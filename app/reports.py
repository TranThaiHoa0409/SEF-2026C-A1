"""Báo cáo PDF (bản chụp số liệu tại lúc tạo) và báo cáo định kỳ."""
import calendar
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from . import alerts, config, db, kpi, notify, pdf

log = logging.getLogger("bizboard.reports")
FMT = "%Y-%m-%d %H:%M:%S"
FREQUENCIES = ("daily", "weekly", "monthly")


class ReportError(Exception):
    """status: 400 thiếu/sai input, 409 cần xác nhận, 422 không có dữ liệu, 500 lỗi PDF."""

    def __init__(self, status: int, message: str, **extra):
        super().__init__(message)
        self.status, self.message, self.extra = status, message, extra


def default_name(kpis: list[str], period_label: str) -> str:
    head = ", ".join(kpis) if len(kpis) <= 2 else f"{kpis[0]} and {len(kpis) - 1} more KPIs"
    return f"{head}, {period_label}"


def _validate(kpis: list[str], period_key: str) -> kpi.Period:
    if not kpis:
        raise ReportError(400, "Choose at least one KPI.")
    unknown = [k for k in kpis if k not in kpi.KPI_NAMES]
    if unknown:
        raise ReportError(400, f"Unknown KPI: {', '.join(unknown)}")
    if len(set(kpis)) != len(kpis):
        raise ReportError(400, "Each KPI can be chosen only once.")
    if period_key not in kpi.DASHBOARD_PERIODS:
        raise ReportError(400, "Choose a valid period: Today, Last 7 days, Last 30 days or This month.")
    return kpi.resolve_period(period_key)


def generate(conn: sqlite3.Connection, owner: dict, kpis: list[str], period_key: str,
             name: Optional[str] = None, confirm_skip: bool = False, schedule_id: Optional[int] = None) -> dict:
    """Tạo báo cáo. KPI không có dữ liệu cần xác nhận "Generate without them" (confirm_skip)."""
    period = _validate(kpis, period_key)
    results = [kpi.compute(conn, k, period) for k in kpi.KPI_NAMES if k in kpis]   # giữ thứ tự KPI chung
    with_data = [r for r in results if r.status == "ok"]
    missing = [r.name for r in results if r.status != "ok"]
    if not with_data:
        raise ReportError(422, f"None of the selected KPIs have data for {period.label}: {period.dates_text}. "
                               "No report was created.", missing=missing)
    if missing and not confirm_skip:
        raise ReportError(409, "Some selected KPIs have no data for this period.", missing=missing,
                          period=period.to_dict())

    name = (name or "").strip() or default_name(kpis, period.label)
    generated_at = datetime.now().strftime(FMT)
    period_text = f"{period.label}: {period.dates_text} {period.end.year}"
    cur = conn.execute(
        "INSERT INTO reports (owner_id, name, kpis_json, period_start, period_end, period_label, generated_at,"
        " schedule_id) VALUES (?,?,?,?,?,?,?,?)",
        (owner["id"], name, json.dumps([r.to_dict() for r in with_data]), period.start.isoformat(),
         period.end.isoformat(), period.label, generated_at, schedule_id),
    )
    report_id = cur.lastrowid
    path = config.reports_dir() / f"report_{report_id}.pdf"
    try:
        pdf.build(path, name, period_text, generated_at, owner["name"],
                  [(r.name, alerts.fmt_value(r.value, r.unit)) for r in with_data])
    except Exception as e:  # noqa: BLE001
        log.warning("PDF for report %s failed: %s", report_id, e)
        path.unlink(missing_ok=True)
        conn.execute("DELETE FROM reports WHERE id = ?", (report_id,))
        raise ReportError(500, "The PDF could not be created, so no report was saved. Please try again.")
    conn.execute("UPDATE reports SET pdf_path = ? WHERE id = ?", (str(path), report_id))
    return get(conn, report_id)


def get(conn: sqlite3.Connection, report_id: int) -> Optional[dict]:
    row = conn.execute("SELECT r.*, u.name AS owner_name FROM reports r JOIN users u ON u.id = r.owner_id"
                       " WHERE r.id = ?", (report_id,)).fetchone()
    if row is None:
        return None
    d = dict(row)
    d["kpis"] = json.loads(d.pop("kpis_json"))
    d["period"] = {"label": d["period_label"], "start": d["period_start"], "end": d["period_end"],
                   "dates_text": kpi.format_range(datetime.fromisoformat(d["period_start"]).date(),
                                                  datetime.fromisoformat(d["period_end"]).date())}
    return d


def delete(conn: sqlite3.Connection, report_id: int) -> None:
    """Xóa báo cáo, bỏ mọi chia sẻ (người nhận mất quyền) và file PDF."""
    r = get(conn, report_id)
    conn.execute("DELETE FROM shares WHERE item_type = 'report' AND item_id = ?", (report_id,))
    conn.execute("DELETE FROM notes WHERE report_id = ?", (report_id,))
    conn.execute("DELETE FROM reports WHERE id = ?", (report_id,))
    if r and r["pdf_path"]:
        Path(r["pdf_path"]).unlink(missing_ok=True)


def list_for(conn: sqlite3.Connection, user_id: str) -> dict:
    cols = "r.id, r.owner_id, u.name AS owner_name, r.name, r.period_label, r.period_start, r.period_end, r.generated_at"
    mine = conn.execute(f"SELECT {cols} FROM reports r JOIN users u ON u.id = r.owner_id"
                        " WHERE r.owner_id = ? ORDER BY r.generated_at DESC, r.id DESC", (user_id,)).fetchall()
    shared = conn.execute(
        f"SELECT DISTINCT {cols} FROM reports r JOIN users u ON u.id = r.owner_id"
        " JOIN shares s ON s.item_type = 'report' AND s.item_id = r.id"
        " WHERE r.owner_id != ? AND ((s.target_type = 'user' AND s.target_id = ?) OR"
        "  (s.target_type = 'group' AND s.target_id IN (SELECT group_id FROM group_members WHERE user_id = ?)))"
        " ORDER BY r.generated_at DESC, r.id DESC", (user_id, user_id, user_id)).fetchall()

    def item(row) -> dict:
        d = dict(row)
        d["dates_text"] = kpi.format_range(datetime.fromisoformat(d["period_start"]).date(),
                                           datetime.fromisoformat(d["period_end"]).date())
        return d
    return {"mine": [item(r) for r in mine], "shared_with_me": [item(r) for r in shared]}


# ------------------------------------------------------------------ lịch định kỳ

def _next_run(at: datetime, frequency: str) -> datetime:
    if frequency == "daily":
        return at + timedelta(days=1)
    if frequency == "weekly":
        return at + timedelta(days=7)
    month = at.month % 12 + 1
    year = at.year + (at.month == 12)
    day = min(at.day, calendar.monthrange(year, month)[1])
    return at.replace(year=year, month=month, day=day)


def _schedule_dict(row) -> dict:
    d = dict(row)
    d["kpis"] = json.loads(d.pop("kpis_json"))
    d["active"] = bool(d["active"])
    d["period_label"] = kpi.PERIOD_LABELS.get(d["period_key"], d["period_key"])
    return d


def _validate_schedule(kpis: list[str], period_key: str, frequency: str, first_run: str) -> datetime:
    _validate(kpis, period_key)
    if frequency not in FREQUENCIES:
        raise ReportError(400, "Choose how often: daily, weekly or monthly.")
    try:
        return datetime.fromisoformat(first_run).replace(second=0, microsecond=0)
    except (TypeError, ValueError):
        raise ReportError(400, "Enter the date and time of the first run.")


def list_schedules(conn: sqlite3.Connection, user_id: str) -> list[dict]:
    rows = conn.execute("SELECT * FROM report_schedules WHERE owner_id = ? ORDER BY id", (user_id,)).fetchall()
    return [_schedule_dict(r) for r in rows]


def get_schedule(conn: sqlite3.Connection, schedule_id: int) -> Optional[dict]:
    row = conn.execute("SELECT * FROM report_schedules WHERE id = ?", (schedule_id,)).fetchone()
    return _schedule_dict(row) if row else None


def create_schedule(conn: sqlite3.Connection, user_id: str, kpis: list[str], period_key: str, frequency: str,
                    first_run: str, name: Optional[str] = None) -> dict:
    run_at = _validate_schedule(kpis, period_key, frequency, first_run)
    name = (name or "").strip() or default_name(kpis, kpi.PERIOD_LABELS[period_key])
    cur = conn.execute("INSERT INTO report_schedules (owner_id, name, kpis_json, period_key, frequency, next_run,"
                       " active) VALUES (?,?,?,?,?,?,1)",
                       (user_id, name, json.dumps(kpis), period_key, frequency, run_at.strftime(FMT)))
    return get_schedule(conn, cur.lastrowid)


def update_schedule(conn: sqlite3.Connection, schedule_id: int, kpis: list[str], period_key: str, frequency: str,
                    first_run: str, name: Optional[str], active: bool) -> dict:
    run_at = _validate_schedule(kpis, period_key, frequency, first_run)
    name = (name or "").strip() or default_name(kpis, kpi.PERIOD_LABELS[period_key])
    conn.execute("UPDATE report_schedules SET name = ?, kpis_json = ?, period_key = ?, frequency = ?, next_run = ?,"
                 " active = ? WHERE id = ?",
                 (name, json.dumps(kpis), period_key, frequency, run_at.strftime(FMT), int(active), schedule_id))
    return get_schedule(conn, schedule_id)


def delete_schedule(conn: sqlite3.Connection, schedule_id: int) -> None:
    conn.execute("DELETE FROM report_schedules WHERE id = ?", (schedule_id,))


def run_due_schedules(at: Optional[datetime] = None) -> list[dict]:
    """Chạy các lịch đến hạn: tạo PDF, thêm vào danh sách, báo cho người dùng; lỗi thì cũng báo."""
    at = at or datetime.now()
    done = []
    with db.get_conn() as conn:
        due = conn.execute("SELECT s.*, u.name AS owner_name FROM report_schedules s JOIN users u ON u.id = s.owner_id"
                           " WHERE s.active = 1 AND s.next_run <= ? ORDER BY s.id", (at.strftime(FMT),)).fetchall()
    for s in due:
        owner = {"id": s["owner_id"], "name": s["owner_name"]}
        with db.get_conn() as conn:
            try:
                report = generate(conn, owner, json.loads(s["kpis_json"]), s["period_key"], s["name"],
                                  confirm_skip=True, schedule_id=s["id"])
                notify.notify(conn, owner["id"], "report", f"Scheduled report ready: {report['name']}",
                              f"Your {s['frequency']} report for {report['period']['label']}: "
                              f"{report['period']['dates_text']} was added to your report list.",
                              link=f"#/report/{report['id']}")
                error = None
                done.append({"schedule_id": s["id"], "report_id": report["id"]})
            except ReportError as e:
                error = e.message
                notify.notify(conn, owner["id"], "report", f"Scheduled report failed: {s['name']}",
                              f"The scheduled report could not be created. {e.message}", link="#/reports")
                done.append({"schedule_id": s["id"], "error": error})
            nxt = datetime.strptime(s["next_run"], FMT)
            while nxt <= at:
                nxt = _next_run(nxt, s["frequency"])
            conn.execute("UPDATE report_schedules SET next_run = ?, last_error = ? WHERE id = ?",
                         (nxt.strftime(FMT), error, s["id"]))
    return done
