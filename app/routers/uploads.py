"""Upload CSV đơn hàng (chỉ System Administrator) và lịch sử upload (chỉ xem)."""
import json

from fastapi import APIRouter, Depends, UploadFile

from .. import auth, db, importer, scheduler

router = APIRouter(prefix="/api/uploads", tags=["uploads"])


@router.post("")
async def upload(file: UploadFile, user: dict = Depends(auth.current_user)):
    auth.require(user, "upload_data")
    content = await file.read()
    with db.get_conn() as conn:
        result = importer.process_upload(conn, file.filename or "upload.csv", content, user["id"])
    if result["status"] == "accepted" and result["rows_loaded"] > 0:
        result["refreshed_at"] = scheduler.refresh(reason=f"upload {result['filename']}")
    return result


@router.get("")
def history(user: dict = Depends(auth.current_user)):
    auth.require(user, "view_upload_history")
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT b.*, u.name AS uploaded_by_name FROM upload_batches b"
            " JOIN users u ON u.id = b.uploaded_by ORDER BY b.id DESC"
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["skipped_rows"] = json.loads(d.pop("skipped_rows_json"))
        d["duplicate_order_ids"] = json.loads(d.pop("duplicate_ids_json"))
        out.append(d)
    return out
