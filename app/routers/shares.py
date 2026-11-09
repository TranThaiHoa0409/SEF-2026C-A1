"""Chia sẻ báo cáo và snapshot, thu hồi quyền."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import auth, db, shares

router = APIRouter(prefix="/api", tags=["shares"])


class ShareBody(BaseModel):
    item_type: str
    item_id: int
    target_type: str
    target_id: str


@router.get("/share-targets")
def targets(user: dict = Depends(auth.current_user)):
    """Người dùng có thể chia sẻ cho, và các nhóm người này đang thuộc."""
    with db.get_conn() as conn:
        return shares.targets(conn, user["id"])


@router.get("/shares")
def list_shares(item_type: str, item_id: int, user: dict = Depends(auth.current_user)):
    with db.get_conn() as conn:
        item = shares.owner_of(conn, item_type, item_id)
        auth.require(user, f"share_{item_type}" if item_type in shares.ITEM_TYPES else "none", item)
        return shares.list_shares(conn, item_type, item_id)


@router.post("/shares")
def create(body: ShareBody, user: dict = Depends(auth.current_user)):
    if body.item_type not in shares.ITEM_TYPES:
        raise HTTPException(400, "Only reports and snapshots can be shared.")
    with db.get_conn() as conn:
        item = shares.owner_of(conn, body.item_type, body.item_id)
        auth.require(user, f"share_{body.item_type}", item)
        try:
            return shares.share(conn, user, body.item_type, body.item_id, body.target_type, body.target_id)
        except shares.ShareError as e:
            raise HTTPException(e.status, e.message)


@router.delete("/shares/{share_id}")
def revoke(share_id: int, user: dict = Depends(auth.current_user)):
    with db.get_conn() as conn:
        s = shares.get_share(conn, share_id)
        item = shares.owner_of(conn, s["item_type"], s["item_id"]) if s else None
        auth.require(user, f"share_{s['item_type']}" if s else "none", item)
        shares.revoke(conn, share_id)
    return {"ok": True}
