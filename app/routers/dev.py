"""Công cụ demo cho System Administrator: hộp thư giả, mô phỏng lỗi, phát lại cảnh báo theo ngày."""
import json
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import alerts, auth, config, db, notify, pdf

router = APIRouter(prefix="/api/dev", tags=["dev"])


class Toggle(BaseModel):
    failing: bool


class Replay(BaseModel):
    start: date
    end: date


def admin(user: dict = Depends(auth.current_user)) -> dict:
    auth.require(user, "dev_tools")
    return user


@router.get("/mailbox")
def mailbox(user: dict = Depends(admin)):
    with db.get_conn() as conn:
        rows = conn.execute("SELECT * FROM mailbox ORDER BY id DESC").fetchall()
    return {"mail_failing": notify.mail_server["failing"], "pdf_failing": pdf.pdf_engine["failing"],
            "items": [dict(r) | {"attempts": json.loads(r["attempts_json"])} for r in rows]}


@router.put("/mail-failure")
def mail_failure(body: Toggle, user: dict = Depends(admin)):
    notify.mail_server["failing"] = body.failing
    return {"mail_failing": body.failing}


@router.put("/pdf-failure")
def pdf_failure(body: Toggle, user: dict = Depends(admin)):
    pdf.pdf_engine["failing"] = body.failing
    return {"pdf_failing": body.failing}


@router.post("/replay-alerts")
def replay_alerts(body: Replay, user: dict = Depends(admin)):
    """Kiểm tra rule lần lượt từng ngày, như thể mỗi ngày có một lần refresh."""
    if body.end < body.start or body.end > config.TODAY:
        raise HTTPException(400, "Choose a valid range that ends no later than today.")
    created = []
    d = body.start
    with db.get_conn() as conn:
        while d <= body.end:
            for nid in alerts.check_rules(conn, d):
                n = conn.execute("SELECT rule_id, user_id, title FROM notifications WHERE id = ?", (nid,)).fetchone()
                created.append({"date": d.isoformat(), **dict(n)})
            d += timedelta(days=1)
    return {"created": created}
