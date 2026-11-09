"""Thông báo trong app và email giả (bảng mailbox).

- Thông báo trong app luôn được lưu, không tắt được.
- Email chỉ gửi khi người nhận có email và công tắc tương ứng đang bật.
- Lần gửi đầu trong vòng 1 phút; lỗi thì thử lại 3 lần, cách nhau 1 phút, dừng khi thành công.
- Thử hết mà vẫn lỗi: ghi log và đánh dấu "email not delivered".
"""
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

from . import config

log = logging.getLogger("bizboard.mail")
FMT = "%Y-%m-%d %H:%M:%S"
NOT_DELIVERED = "email not delivered"

# Mô phỏng máy chủ mail lỗi (Admin bật/tắt khi demo).
mail_server = {"failing": False}


def now() -> datetime:
    return datetime.now()


# ------------------------------------------------------------------ cài đặt

def get_settings(conn: sqlite3.Connection, user_id: str) -> dict:
    row = conn.execute("SELECT email_on_alert, email_on_share FROM notification_settings WHERE user_id = ?",
                       (user_id,)).fetchone()
    email = conn.execute("SELECT email FROM users WHERE id = ?", (user_id,)).fetchone()["email"]
    return {"email_on_alert": bool(row["email_on_alert"]) if row else True,
            "email_on_share": bool(row["email_on_share"]) if row else True,
            "email": email, "has_email": bool(email)}


def save_settings(conn: sqlite3.Connection, user_id: str, email_on_alert: bool, email_on_share: bool) -> dict:
    conn.execute(
        "INSERT INTO notification_settings (user_id, email_on_alert, email_on_share) VALUES (?,?,?)"
        " ON CONFLICT(user_id) DO UPDATE SET email_on_alert = excluded.email_on_alert,"
        " email_on_share = excluded.email_on_share",
        (user_id, int(email_on_alert), int(email_on_share)),
    )
    return get_settings(conn, user_id)


# ------------------------------------------------------------------ tạo thông báo

def notify(conn: sqlite3.Connection, user_id: str, kind: str, title: str, body: str,
           email_type: Optional[str] = None, link: Optional[str] = None, **alert_fields) -> int:
    """Lưu thông báo trong app; email_type ('alert' | 'share') nếu cần gửi email."""
    created = now().strftime(FMT)
    email_status = None
    to_email = None
    if email_type:
        s = get_settings(conn, user_id)
        if not s["has_email"]:
            email_status = "in-app only (no email address)"
        elif not s[f"email_on_{email_type}"]:
            email_status = "in-app only (email turned off)"
        else:
            email_status = "pending"
            to_email = s["email"]
    cur = conn.execute(
        "INSERT INTO notifications (user_id, kind, title, body, rule_id, kpi, condition, threshold, value,"
        " data_date, link, created_at, email_status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (user_id, kind, title, body, alert_fields.get("rule_id"), alert_fields.get("kpi"),
         alert_fields.get("condition"), alert_fields.get("threshold"), alert_fields.get("value"),
         alert_fields.get("data_date"), link, created, email_status),
    )
    nid = cur.lastrowid
    if to_email:
        conn.execute(
            "INSERT INTO mailbox (notification_id, to_user_id, to_email, subject, body, status, queued_at,"
            " next_attempt_at) VALUES (?,?,?,?,?, 'pending', ?, ?)",
            (nid, user_id, to_email, f"BizBoard: {title}", body, created, created),
        )
    return nid


def list_for(conn: sqlite3.Connection, user_id: str) -> list[dict]:
    """Chưa đọc lên trước, mới nhất lên trước."""
    rows = conn.execute("SELECT * FROM notifications WHERE user_id = ? ORDER BY is_read, created_at DESC, id DESC",
                        (user_id,)).fetchall()
    return [dict(r) | {"is_read": bool(r["is_read"])} for r in rows]


def mark_read(conn: sqlite3.Connection, user_id: str, notification_id: int) -> bool:
    cur = conn.execute("UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?",
                       (notification_id, user_id))
    return cur.rowcount == 1


# ------------------------------------------------------------------ gửi email giả

def _send(row: sqlite3.Row) -> None:
    """Máy chủ mail giả: lỗi khi đang mô phỏng lỗi."""
    if mail_server["failing"]:
        raise ConnectionError("Mail server is not responding (simulated).")


def process_mailbox(conn: sqlite3.Connection, at: Optional[datetime] = None) -> int:
    """Gửi các email đến lượt. Trả số email đã xử lý."""
    at = at or now()
    due = conn.execute("SELECT * FROM mailbox WHERE status = 'pending' AND next_attempt_at <= ? ORDER BY id",
                       (at.strftime(FMT),)).fetchall()
    for row in due:
        attempt = row["attempt"] + 1
        attempts = json.loads(row["attempts_json"])
        try:
            _send(row)
        except Exception as e:  # noqa: BLE001 - mọi lỗi gửi đều được thử lại
            attempts.append({"at": at.strftime(FMT), "ok": False, "error": str(e)})
            if attempt > config.MAIL_RETRIES:   # lần đầu + 3 lần thử lại đều lỗi
                conn.execute("UPDATE mailbox SET attempt = ?, status = 'failed', attempts_json = ? WHERE id = ?",
                             (attempt, json.dumps(attempts), row["id"]))
                conn.execute("UPDATE notifications SET email_status = ? WHERE id = ?",
                             (NOT_DELIVERED, row["notification_id"]))
                conn.execute("INSERT INTO activity_log (actor_id, action, target, created_at) VALUES (?,?,?,?)",
                             ("system", "email_failed", f"mailbox {row['id']} to {row['to_email']}", at.strftime(FMT)))
                log.warning("Email %s to %s not delivered after %s attempts", row["id"], row["to_email"], attempt)
            else:
                nxt = at + timedelta(seconds=config.MAIL_RETRY_SECONDS)
                conn.execute("UPDATE mailbox SET attempt = ?, next_attempt_at = ?, attempts_json = ? WHERE id = ?",
                             (attempt, nxt.strftime(FMT), json.dumps(attempts), row["id"]))
            continue
        attempts.append({"at": at.strftime(FMT), "ok": True})
        conn.execute("UPDATE mailbox SET attempt = ?, status = 'sent', sent_at = ?, attempts_json = ? WHERE id = ?",
                     (attempt, at.strftime(FMT), json.dumps(attempts), row["id"]))
        conn.execute("UPDATE notifications SET email_status = 'sent' WHERE id = ?", (row["notification_id"],))
    return len(due)
