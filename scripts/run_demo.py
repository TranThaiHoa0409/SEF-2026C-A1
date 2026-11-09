"""Tạo một DB demo có sẵn tình huống (để chụp ảnh SRS) rồi chạy app trên cổng 8001.

Chạy: .venv/Scripts/python scripts/run_demo.py
DB demo (demo.db) và PDF (demo_reports/) tách khỏi bizboard.db, mỗi lần chạy tạo lại từ đầu.
"""
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["BIZBOARD_DB"] = str(ROOT / "demo.db")
os.environ["BIZBOARD_REPORTS"] = str(ROOT / "demo_reports")


def seed() -> None:
    os.environ["BIZBOARD_NO_SCHEDULER"] = "1"
    Path(os.environ["BIZBOARD_DB"]).unlink(missing_ok=True)
    shutil.rmtree(os.environ["BIZBOARD_REPORTS"], ignore_errors=True)

    from fastapi.testclient import TestClient

    from app import db, notify
    from app.main import app

    def as_user(c, user_id):
        c.post("/api/auth/login", json={"user_id": user_id})

    def ok(r):
        assert r.status_code == 200, r.text
        return r.json()

    with TestClient(app) as c:
        # Cảnh báo trước tiên: phát lại 1 đến 7 Nov như mỗi ngày có một lần refresh
        as_user(c, "U01")
        ok(c.post("/api/dev/replay-alerts", json={"start": "2026-11-01", "end": "2026-11-07"}))

        # Admin: hai lần upload để có lịch sử (refresh sau upload không tạo alert trùng: 7 Nov đang vượt ngưỡng)
        for name in ("upload_02_missing_column_order_value.csv", "upload_03_bad_dates.csv"):
            with open(ROOT / "data" / name, "rb") as f:
                c.post("/api/uploads", files={"file": (name, f, "text/csv")})

        # Hoa: dashboard có số và biểu đồ, một snapshot
        as_user(c, "U02")
        ok(c.put("/api/dashboard/selection", json={"widget_ids": [
            "total_revenue.summary", "total_sales.summary", "average_order_value.summary",
            "new_customers.summary", "active_users.summary", "conversion_rate.summary",
            "total_revenue.chart", "active_users.chart"]}))
        ok(c.post("/api/snapshots", json={"name": "Weekly check, 1 to 7 Nov"}))
        grp = ok(c.post("/api/groups", json={"name": "Regional managers"}))   # cho activity log
        ok(c.post(f"/api/groups/{grp['group_id']}/members", json={"user_id": "U05"}))

        # Phu: báo cáo chia sẻ cho Sales Team và riêng cho Hoa, snapshot chia sẻ cho Sales Team, lịch tuần
        as_user(c, "U04")
        rep = ok(c.post("/api/reports", json={"kpis": ["Total Sales", "Average Order Value", "Total Revenue",
                                                       "Revenue Growth"], "period_key": "last_7_days",
                                              "name": "Weekly sales review"}))
        for target_type, target_id in (("group", "G01"), ("user", "U02")):
            ok(c.post("/api/shares", json={"item_type": "report", "item_id": rep["id"],
                                           "target_type": target_type, "target_id": target_id}))
        snap = ok(c.post("/api/snapshots", json={"name": "Sales dashboard"}))
        ok(c.post("/api/shares", json={"item_type": "snapshot", "item_id": snap["id"],
                                       "target_type": "group", "target_id": "G01"}))
        ok(c.post("/api/schedules", json={"kpis": ["Total Revenue", "Total Sales"], "period_key": "last_7_days",
                                          "frequency": "weekly", "first_run": "2026-11-16T08:00",
                                          "name": "Monday sales summary"}))
        ok(c.post(f"/api/reports/{rep['id']}/notes", json={"body": "Sales fell after the payment gateway issue."}))

        # Len, Mai viết ghi chú (nhận qua nhóm)
        as_user(c, "U03")
        ok(c.post(f"/api/reports/{rep['id']}/notes",
                  json={"body": "Revenue dropped below $1,000 on 3, 4 and 7 Nov. Gateway incident?"}))
        as_user(c, "U06")
        ok(c.post(f"/api/reports/{rep['id']}/notes", json={"body": "Marketplace orders look normal."}))

        with db.get_conn() as conn:   # gửi email giả đang chờ
            notify.process_mailbox(conn)

    os.environ.pop("BIZBOARD_NO_SCHEDULER")


if __name__ == "__main__":
    seed()
    import uvicorn
    uvicorn.run("app.main:app", port=int(os.environ.get("PORT", "8001")))
