"""Bước 6: kiểm tra tự động các NFR đo được trong prototype.

NFR-04, NFR-10 (email) có trong test_reports_alerts.py; NFR-05 (no access) rải trong mọi file test.
NFR-07, 08, 09, 12, 13 và phần 44px của NFR-14 kiểm thủ công: xem docs/NFR_review.md.
"""
import time

import pytest

from app import config, dashboard, scheduler
from conftest import ADMIN, HOA, PHU, login

ALL_KPIS = ["Total Sales", "Average Order Value", "Total Revenue", "Revenue Growth", "New Customers",
            "Customer Retention Rate", "Active Users", "Conversion Rate"]


def test_nfr01_dashboard_within_3_seconds(client):
    """95% lượt xem dashboard dưới 3 giây: đo 20 lượt với đủ 13 widget, mọi kỳ."""
    login(client, HOA)
    client.put("/api/dashboard/selection", json={"widget_ids": [w.id for w in dashboard.CATALOGUE]})
    times = []
    for period in ("today", "last_7_days", "last_30_days", "this_month") * 5:
        client.put("/api/dashboard/period", json={"period_key": period})
        t = time.perf_counter()
        assert client.get("/api/dashboard").status_code == 200
        times.append(time.perf_counter() - t)
    times.sort()
    assert times[int(len(times) * 0.95) - 1] < 3.0


def test_nfr02_pdf_within_10_seconds(client):
    login(client, PHU)
    t = time.perf_counter()
    r = client.post("/api/reports", json={"kpis": ALL_KPIS, "period_key": "last_30_days"})
    elapsed = time.perf_counter() - t
    assert r.status_code == 200
    assert client.get("/api/reports").json()["mine"][0]["id"] == r.json()["id"]   # đã vào danh sách
    assert elapsed < 10.0


def test_nfr03_refresh_every_5_minutes_and_on_upload(client, monkeypatch):
    assert config.REFRESH_INTERVAL_MINUTES == 5
    jobs = {}

    class FakeScheduler:
        def add_job(self, fn, trigger, id, **kw):
            jobs[id] = kw

        def start(self):
            pass

    monkeypatch.setattr(scheduler, "BackgroundScheduler", FakeScheduler)
    monkeypatch.setattr(scheduler, "_scheduler", None)
    scheduler.start()
    monkeypatch.setattr(scheduler, "_scheduler", None)
    assert jobs["refresh"]["minutes"] == 5
    assert jobs["mail"]["seconds"] < 60          # NFR-04: lần gửi đầu trong 1 phút

    login(client, ADMIN)
    before = scheduler.last_refresh()
    with open(config.DATA_DIR / "upload_08_new_and_changed_orders.csv", "rb") as f:
        client.post("/api/uploads", files={"file": ("u8.csv", f, "text/csv")})
    after = scheduler.last_refresh()
    assert after != before and after["reason"].startswith("upload")


PUBLIC = {("GET", "/api/auth/accounts"), ("POST", "/api/auth/login"), ("POST", "/api/auth/logout")}


def _api_routes():
    """Mọi endpoint /api lấy từ OpenAPI của app (gồm cả router con)."""
    from app.main import app
    for path, ops in app.openapi()["paths"].items():
        for method in ops:
            if path.startswith("/api") and (method.upper(), path) not in PUBLIC:
                yield method.upper(), path


@pytest.mark.parametrize("method,path", sorted(set(_api_routes())))
def test_nfr06_every_data_endpoint_needs_sign_in(client, method, path):
    url = path.replace("{", "").replace("}", "")   # tham số giả; phải bị chặn trước khi đọc
    for name in ("report_id", "snapshot_id", "schedule_id", "share_id", "note_id", "notification_id"):
        url = url.replace(name, "1")
    r = client.request(method, url, json={})
    assert r.status_code == 401, f"{method} {path} -> {r.status_code}"


def test_nfr11_saved_items_survive_restart(client):
    login(client, PHU)
    client.put("/api/dashboard/selection", json={"widget_ids": ["total_sales.summary", "total_revenue.chart"]})
    rep = client.post("/api/reports", json={"kpis": ["Total Revenue"], "period_key": "last_7_days"}).json()
    client.post(f"/api/reports/{rep['id']}/notes", json={"body": "Kept after restart"})
    client.post("/api/alert-rules", json={"kpi": "Total Sales", "condition": "below", "threshold": 50})
    grp = client.post("/api/groups", json={"name": "Restart check"}).json()

    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as restarted:      # khởi động lại app trên cùng file DB
        login(restarted, PHU)
        assert [w["id"] for w in restarted.get("/api/dashboard").json()["widgets"]] == \
            ["total_sales.summary", "total_revenue.chart"]
        assert restarted.get(f"/api/reports/{rep['id']}").status_code == 200
        assert restarted.get(f"/api/reports/{rep['id']}/notes").json()["items"][0]["body"] == "Kept after restart"
        assert "Total Sales goes below 50" in [r["text"] for r in restarted.get("/api/alert-rules").json()]
        assert grp["group_id"] in [g["group_id"] for g in restarted.get("/api/groups").json()]


def test_nfr14_css_sets_44px_minimum():
    """Phần đo trên màn hình 360px làm trong trình duyệt; ở đây kiểm tra quy tắc CSS chung."""
    css = (config.STATIC_DIR / "style.css").read_text(encoding="utf-8")
    assert "button, select, input[type=file], input[type=search] { min-height: 44px; min-width: 44px;" in css
    assert "nav a { display: inline-flex; align-items: center; min-height: 44px;" in css


def test_api_responses_are_not_cached(client):
    """Đổi tài khoản trên cùng trình duyệt không được thấy dữ liệu của người trước."""
    login(client, HOA)
    assert client.get("/api/dashboard").headers["cache-control"] == "no-store"
