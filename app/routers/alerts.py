"""Rule cảnh báo, danh sách thông báo trong app, công tắc email."""
from typing import Optional, Union

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import alerts, auth, db, notify

router = APIRouter(prefix="/api", tags=["alerts"])


class RuleBody(BaseModel):
    kpi: str = ""
    condition: str = ""
    threshold: Optional[Union[float, str]] = None
    is_active: bool = True


class SettingsBody(BaseModel):
    email_on_alert: bool
    email_on_share: bool


def _rule_for(user: dict, rule_id: str) -> dict:
    with db.get_conn() as conn:
        rule = alerts.get_rule(conn, rule_id)
    auth.require(user, "manage_rule", rule)
    return rule


@router.get("/alert-rules")
def list_rules(user: dict = Depends(auth.current_user)):
    with db.get_conn() as conn:
        return alerts.list_rules(conn, user["id"])


@router.post("/alert-rules")
def create_rule(body: RuleBody, user: dict = Depends(auth.current_user)):
    try:
        with db.get_conn() as conn:
            return alerts.create_rule(conn, user["id"], body.kpi, body.condition, body.threshold)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.put("/alert-rules/{rule_id}")
def update_rule(rule_id: str, body: RuleBody, user: dict = Depends(auth.current_user)):
    _rule_for(user, rule_id)
    try:
        with db.get_conn() as conn:
            return alerts.update_rule(conn, rule_id, body.kpi, body.condition, body.threshold, body.is_active)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete("/alert-rules/{rule_id}")
def delete_rule(rule_id: str, user: dict = Depends(auth.current_user)):
    _rule_for(user, rule_id)
    with db.get_conn() as conn:
        alerts.delete_rule(conn, rule_id)
    return {"ok": True}


@router.get("/notifications")
def notifications(user: dict = Depends(auth.current_user)):
    with db.get_conn() as conn:
        items = notify.list_for(conn, user["id"])
    return {"unread": sum(not n["is_read"] for n in items), "items": items}


@router.post("/notifications/{notification_id}/read")
def mark_read(notification_id: int, user: dict = Depends(auth.current_user)):
    with db.get_conn() as conn:
        if not notify.mark_read(conn, user["id"], notification_id):
            raise HTTPException(403, auth.NO_ACCESS)
    return {"ok": True}


@router.get("/notification-settings")
def get_settings(user: dict = Depends(auth.current_user)):
    with db.get_conn() as conn:
        return notify.get_settings(conn, user["id"])


@router.put("/notification-settings")
def save_settings(body: SettingsBody, user: dict = Depends(auth.current_user)):
    with db.get_conn() as conn:
        return notify.save_settings(conn, user["id"], body.email_on_alert, body.email_on_share)
