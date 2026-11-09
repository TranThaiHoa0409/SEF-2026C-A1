"""Đăng nhập mẫu, phiên 30 phút, thông báo no access."""
from datetime import datetime, timedelta

from app import auth
from conftest import ADMIN, HOA, NAM, login


def test_accounts_list_has_8_sample_users(client):
    accounts = client.get("/api/auth/accounts").json()
    assert [a["name"] for a in accounts] == ["Admin An", "Hoa", "Len", "Phu", "Yuki", "Mai", "Bao", "Nam"]
    assert [a["is_active"] for a in accounts].count(False) == 1


def test_data_needs_sign_in(client):
    assert client.get("/api/kpis").status_code == 401


def test_deactivated_user_cannot_sign_in(client):
    r = client.post("/api/auth/login", json={"user_id": NAM})
    assert r.status_code == 403
    assert "deactivated" in r.json()["detail"]


def test_sign_in_and_out(client):
    user = login(client, HOA)
    assert user["name"] == "Hoa" and not user["is_admin"]
    assert client.get("/api/auth/me").json()["id"] == HOA
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401


def test_session_ends_after_30_minutes_idle(client, monkeypatch):
    start = datetime(2026, 11, 8, 9, 0, 0)
    monkeypatch.setattr(auth, "now", lambda: start)
    login(client, ADMIN)
    monkeypatch.setattr(auth, "now", lambda: start + timedelta(minutes=29))
    assert client.get("/api/auth/me").status_code == 200   # còn hoạt động, đặt lại mốc
    monkeypatch.setattr(auth, "now", lambda: start + timedelta(minutes=58))
    assert client.get("/api/auth/me").status_code == 200   # 29 phút sau lần trước
    monkeypatch.setattr(auth, "now", lambda: start + timedelta(minutes=89))
    assert client.get("/api/auth/me").status_code == 401   # 31 phút không hoạt động


def test_kpis_endpoint(client):
    login(client, HOA)
    data = client.get("/api/kpis?period=last_7_days").json()
    assert data["period"]["dates_text"] == "1 to 7 Nov"
    v = {k["name"]: k["value"] for k in data["kpis"]}
    assert v["Total Sales"] == 421 and v["Total Revenue"] == 15641.04
    north = client.get("/api/kpis", params={"start": "2026-11-01", "end": "2026-11-07",
                                             "filter": "region:North"}).json()
    assert north["filter"]["label"] == "Region: North"
    assert {k["name"]: k["value"] for k in north["kpis"]}["Total Sales"] == 147


def test_kpis_bad_input(client):
    login(client, HOA)
    assert client.get("/api/kpis?period=yesterday").status_code == 400
    assert client.get("/api/kpis?start=2026-11-07&end=2026-11-01").status_code == 400
    assert client.get("/api/kpis?start=2026-11-01&end=2026-11-20").status_code == 400
    assert client.get("/api/kpis?filter=colour:red").status_code == 400
