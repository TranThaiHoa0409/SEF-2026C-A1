"""Snapshot dashboard: chụp, liệt kê (của tôi và Shared with me), xem, xóa.

Snapshot chỉ xem, không có ghi chú. Chia sẻ snapshot làm ở bước 4 cùng chia sẻ báo cáo.
"""
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from .. import auth, dashboard, db

router = APIRouter(prefix="/api/snapshots", tags=["snapshots"])

LIST_COLUMNS = "s.id, s.owner_id, u.name AS owner_name, s.name, s.period_start, s.period_end, s.captured_at"


class CaptureBody(BaseModel):
    name: Optional[str] = None


def _get(snapshot_id: int) -> Optional[dict]:
    with db.get_conn() as conn:
        row = conn.execute("SELECT * FROM snapshots WHERE id = ?", (snapshot_id,)).fetchone()
    return dict(row) if row else None


def _summary(row) -> dict:
    d = dict(row)
    data = json.loads(d.pop("data_json")) if "data_json" in d else None
    if data:
        d["period"] = data["period"]
    return d


@router.post("")
def capture(body: CaptureBody, user: dict = Depends(auth.current_user)):
    with db.get_conn() as conn:
        data = dashboard.build(conn, user["id"])
        name = (body.name or "").strip() or dashboard.default_snapshot_name(data["period"]["label"])
        captured_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur = conn.execute(
            "INSERT INTO snapshots (owner_id, name, period_start, period_end, captured_at, data_json)"
            " VALUES (?,?,?,?,?,?)",
            (user["id"], name, data["period"]["start"], data["period"]["end"], captured_at, json.dumps(data)),
        )
    return {"id": cur.lastrowid, "name": name, "captured_at": captured_at, "period": data["period"]}


@router.get("")
def list_snapshots(user: dict = Depends(auth.current_user)):
    with db.get_conn() as conn:
        mine = conn.execute(
            f"SELECT {LIST_COLUMNS}, s.data_json FROM snapshots s JOIN users u ON u.id = s.owner_id"
            " WHERE s.owner_id = ? ORDER BY s.captured_at DESC, s.id DESC", (user["id"],)
        ).fetchall()
        shared = conn.execute(
            f"SELECT DISTINCT {LIST_COLUMNS}, s.data_json FROM snapshots s JOIN users u ON u.id = s.owner_id"
            " JOIN shares sh ON sh.item_type = 'snapshot' AND sh.item_id = s.id"
            " WHERE s.owner_id != ? AND ("
            "  (sh.target_type = 'user' AND sh.target_id = ?) OR"
            "  (sh.target_type = 'group' AND sh.target_id IN"
            "    (SELECT group_id FROM group_members WHERE user_id = ?)))"
            " ORDER BY s.captured_at DESC, s.id DESC", (user["id"], user["id"], user["id"])
        ).fetchall()
    return {"mine": [_summary(r) for r in mine], "shared_with_me": [_summary(r) for r in shared]}


@router.get("/{snapshot_id}")
def view(snapshot_id: int, user: dict = Depends(auth.current_user)):
    snap = _get(snapshot_id)
    auth.require(user, "view_snapshot", snap)
    data = json.loads(snap.pop("data_json"))
    return snap | {"data": data, "can_delete": snap["owner_id"] == user["id"]}


@router.delete("/{snapshot_id}")
def delete(snapshot_id: int, user: dict = Depends(auth.current_user)):
    snap = _get(snapshot_id)
    auth.require(user, "delete_snapshot", snap)
    with db.get_conn() as conn:
        conn.execute("DELETE FROM shares WHERE item_type = 'snapshot' AND item_id = ?", (snapshot_id,))
        conn.execute("DELETE FROM snapshots WHERE id = ?", (snapshot_id,))
    return {"ok": True}
