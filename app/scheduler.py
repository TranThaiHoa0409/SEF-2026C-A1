"""Tác vụ nền: refresh dữ liệu mỗi 5 phút, hoặc ngay sau upload hợp lệ.

Các bước sau gắn thêm việc chạy sau mỗi lần refresh (kiểm tra rule cảnh báo,
gửi email giả, chạy báo cáo đến lịch) qua AFTER_REFRESH.
"""
import logging
from datetime import datetime
from typing import Callable, Optional

from apscheduler.schedulers.background import BackgroundScheduler

from . import config, db

log = logging.getLogger("bizboard.scheduler")

# Mỗi hàm nhận (conn) và chạy trong cùng giao dịch với lần refresh.
AFTER_REFRESH: list[Callable] = []

_scheduler: Optional[BackgroundScheduler] = None


def refresh(reason: str = "scheduled") -> str:
    """Ghi nhận một lần refresh và chạy các việc phụ thuộc. Trả thời điểm refresh."""
    at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with db.get_conn() as conn:
        conn.execute("INSERT INTO refresh_log (refreshed_at, reason) VALUES (?, ?)", (at, reason))
        for hook in AFTER_REFRESH:
            hook(conn)
    log.info("Data refreshed (%s) at %s", reason, at)
    return at


def last_refresh() -> Optional[dict]:
    with db.get_conn() as conn:
        row = conn.execute("SELECT refreshed_at, reason FROM refresh_log ORDER BY id DESC LIMIT 1").fetchone()
    return dict(row) if row else None


def send_mail() -> None:
    from . import notify
    with db.get_conn() as conn:
        notify.process_mailbox(conn)


def run_schedules() -> None:
    from . import reports
    reports.run_due_schedules()


def _check_alerts(conn) -> None:
    from . import alerts
    alerts.check_rules(conn)


AFTER_REFRESH.append(_check_alerts)


def start() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(refresh, "interval", minutes=config.REFRESH_INTERVAL_MINUTES,
                       id="refresh", next_run_time=datetime.now())
    _scheduler.add_job(send_mail, "interval", seconds=config.MAIL_POLL_SECONDS, id="mail")
    _scheduler.add_job(run_schedules, "interval", seconds=config.SCHEDULE_POLL_SECONDS, id="schedules")
    _scheduler.start()


def stop() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
