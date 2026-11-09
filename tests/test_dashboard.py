"""Bước 2: danh mục widget, lưu lựa chọn, bố cục, kỳ, snapshot."""
import json

from app import auth, db
from conftest import ADMIN, DATA, HOA, PHU, login

DEFAULT = ["total_revenue.summary", "total_sales.summary", "new_customers.summary", "active_users.summary"]
LEN, MAI, YUKI = "U03", "U06", "U05"


def ids(client):
    return [w["id"] for w in client.get("/api/dashboard").json()["widgets"]]


# ------------------------------------------------------------------ danh mục

def test_catalogue_has_13_widgets_grouped(client):
    login(client, HOA)
    cat = client.get("/api/widgets").json()
    assert cat["groups"] == ["Sales", "Revenue", "Customers", "App usage"]
    widgets = cat["widgets"]
    assert len(widgets) == 13
    assert sum(w["type"] == "summary" for w in widgets) == 8
    assert {w["kpi"] for w in widgets if w["type"] == "chart"} == {
        "Total Sales", "Average Order Value", "Total Revenue", "New Customers", "Active Users"}
    groups = [w["group"] for w in widgets]
    assert groups == sorted(groups, key=cat["groups"].index)   # theo nhóm
    assert {w["id"] for w in widgets if w["added"]} == set(DEFAULT)


def test_catalogue_marks_no_data_for_period(client):
    login(client, HOA)
    client.put("/api/dashboard/period", json={"period_key": "today"})   # 8 Nov chưa có dữ liệu
    cat = client.get("/api/widgets").json()
    assert all(w["no_data"] for w in cat["widgets"])
    assert len(cat["widgets"]) == 13   # vẫn hiện đủ


def test_catalogue_same_for_everyone(client):
    login(client, HOA)
    a = [w["id"] for w in client.get("/api/widgets").json()["widgets"]]
    login(client, PHU)
    b = [w["id"] for w in client.get("/api/widgets").json()["widgets"]]
    assert a == b


# ------------------------------------------------------------------ lựa chọn

def test_new_user_gets_default_set_and_period(client):
    login(client, HOA)
    d = client.get("/api/dashboard").json()
    assert [w["id"] for w in d["widgets"]] == DEFAULT
    assert d["period"]["key"] == "last_7_days" and d["period"]["dates_text"] == "1 to 7 Nov"
    values = {w["kpi"]: w["value"] for w in d["widgets"]}
    assert values == {"Total Revenue": 15641.04, "Total Sales": 421, "New Customers": 112, "Active Users": 1240}


def test_save_selection_keeps_order_and_adds_new_at_end(client):
    login(client, HOA)
    client.put("/api/dashboard/layout", json={"widget_ids": list(reversed(DEFAULT))})
    r = client.put("/api/dashboard/selection", json={"widget_ids": [
        "total_revenue.summary", "conversion_rate.summary", "total_sales.summary", "total_revenue.chart"]})
    assert r.status_code == 200
    assert ids(client) == ["total_sales.summary", "total_revenue.summary",
                           "conversion_rate.summary", "total_revenue.chart"]


def test_selection_validation(client):
    login(client, HOA)
    dup = client.put("/api/dashboard/selection", json={"widget_ids": ["total_sales.summary"] * 2})
    assert dup.status_code == 400 and "twice" in dup.json()["detail"]
    assert client.put("/api/dashboard/selection", json={"widget_ids": ["nope"]}).status_code == 400
    assert client.put("/api/dashboard/selection", json={"widget_ids": []}).status_code == 400
    assert ids(client) == DEFAULT   # không lưu gì


def test_two_users_have_independent_dashboards(client):
    login(client, HOA)
    client.put("/api/dashboard/selection", json={"widget_ids": ["conversion_rate.summary"]})
    client.put("/api/dashboard/period", json={"period_key": "last_30_days"})
    login(client, PHU)
    d = client.get("/api/dashboard").json()
    assert [w["id"] for w in d["widgets"]] == DEFAULT and d["period"]["key"] == "last_7_days"
    login(client, HOA)
    d = client.get("/api/dashboard").json()
    assert [w["id"] for w in d["widgets"]] == ["conversion_rate.summary"]
    assert d["period"]["dates_text"] == "9 Oct to 7 Nov"


def test_choices_survive_sign_out_and_restart(client):
    login(client, HOA)
    client.put("/api/dashboard/selection", json={"widget_ids": DEFAULT + ["active_users.chart"]})
    client.put("/api/dashboard/layout", json={"widget_ids": ["active_users.chart"] + DEFAULT})
    client.put("/api/dashboard/period", json={"period_key": "this_month"})
    client.post("/api/auth/logout")
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as other:   # "thiết bị khác", app khởi động lại
        login(other, HOA)
        d = other.get("/api/dashboard").json()
    assert [w["id"] for w in d["widgets"]] == ["active_users.chart"] + DEFAULT
    assert d["period"]["key"] == "this_month"


def test_reset_selection(client):
    login(client, HOA)
    client.put("/api/dashboard/selection", json={"widget_ids": ["conversion_rate.summary"]})
    client.put("/api/dashboard/period", json={"period_key": "today"})
    client.post("/api/dashboard/reset")
    assert ids(client) == DEFAULT
    assert client.get("/api/dashboard").json()["period"]["key"] == "today"   # kỳ giữ nguyên


# ------------------------------------------------------------------ bố cục

def test_layout_saves_and_resets(client):
    login(client, HOA)
    new_order = ["active_users.summary", "total_sales.summary", "new_customers.summary", "total_revenue.summary"]
    assert client.put("/api/dashboard/layout", json={"widget_ids": new_order}).status_code == 200
    assert ids(client) == new_order
    client.post("/api/dashboard/layout/reset")
    assert ids(client) == ["total_sales.summary", "total_revenue.summary",
                           "new_customers.summary", "active_users.summary"]   # thứ tự danh mục


def test_layout_must_match_selection(client):
    login(client, HOA)
    r = client.put("/api/dashboard/layout", json={"widget_ids": DEFAULT[:3]})
    assert r.status_code == 400
    r = client.put("/api/dashboard/layout", json={"widget_ids": DEFAULT[:3] + ["conversion_rate.summary"]})
    assert r.status_code == 400


def test_removing_widget_moves_others_up(client):
    login(client, HOA)
    client.put("/api/dashboard/selection", json={"widget_ids": [DEFAULT[0], DEFAULT[2], DEFAULT[3]]})
    assert ids(client) == [DEFAULT[0], DEFAULT[2], DEFAULT[3]]


def test_widget_removed_from_catalogue_is_skipped(client):
    login(client, HOA)
    with db.get_conn() as conn:
        conn.execute("INSERT INTO dashboard_prefs VALUES (?,?,?)",
                     (HOA, json.dumps(["old.widget", "total_sales.summary"]), "last_7_days"))
    d = client.get("/api/dashboard").json()
    assert [w["id"] for w in d["widgets"]] == ["total_sales.summary"]
    assert "no longer available" in d["skipped"][0]


# ------------------------------------------------------------------ kỳ và widget

def test_period_validation(client):
    login(client, HOA)
    assert client.put("/api/dashboard/period", json={"period_key": "yesterday"}).status_code == 400


def test_no_data_widget_shows_message(client):
    login(client, HOA)
    client.put("/api/dashboard/period", json={"period_key": "today"})
    w = client.get("/api/dashboard").json()["widgets"][0]
    assert w["value"] is None and w["status"] == "no_data" and "8 Nov" in w["message"]


def test_chart_widget_points(client):
    login(client, HOA)
    client.put("/api/dashboard/selection", json={"widget_ids": ["total_revenue.chart"]})
    w = client.get("/api/dashboard").json()["widgets"][0]
    assert w["granularity"] == "day" and len(w["points"]) == 7
    assert w["points"][2]["label"] == "3 Nov" and w["points"][2]["value"] == 662.5
    assert round(sum(p["value"] for p in w["points"]), 2) == 15641.04
    client.put("/api/dashboard/period", json={"period_key": "today"})
    w = client.get("/api/dashboard").json()["widgets"][0]
    assert w["granularity"] == "hour" and len(w["points"]) == 24 and w["status"] == "no_data"


# ------------------------------------------------------------------ snapshot

def share(item_id: int, target_type: str, target_id: str):
    with db.get_conn() as conn:
        conn.execute("INSERT INTO shares (item_type, item_id, target_type, target_id, created_at)"
                     " VALUES ('snapshot', ?, ?, ?, '2026-11-08 09:00:00')", (item_id, target_type, target_id))


def test_capture_snapshot_does_not_change_after_refresh(client):
    login(client, HOA)
    snap = client.post("/api/snapshots", json={}).json()
    assert snap["name"] == "Dashboard, Last 7 days"
    login(client, ADMIN)
    with open(DATA / "upload_08_new_and_changed_orders.csv", "rb") as f:
        client.post("/api/uploads", files={"file": ("upload_08.csv", f, "text/csv")})
    login(client, HOA)
    live = {w["kpi"]: w["value"] for w in client.get("/api/dashboard").json()["widgets"]}
    assert live["Total Sales"] == 430
    view = client.get(f"/api/snapshots/{snap['id']}").json()
    frozen = {w["kpi"]: w["value"] for w in view["data"]["widgets"]}
    assert frozen["Total Sales"] == 421 and frozen["Total Revenue"] == 15641.04
    assert view["data"]["period"]["dates_text"] == "1 to 7 Nov" and view["captured_at"]


def test_snapshot_lists_and_access(client):
    login(client, PHU)
    own = client.post("/api/snapshots", json={"name": "Sales check"}).json()
    lst = client.get("/api/snapshots").json()
    assert [s["name"] for s in lst["mine"]] == ["Sales check"] and lst["shared_with_me"] == []
    assert lst["mine"][0]["period"]["dates_text"] == "1 to 7 Nov"

    login(client, HOA)
    r = client.get(f"/api/snapshots/{own['id']}")
    assert r.status_code == 403 and r.json()["detail"] == auth.NO_ACCESS
    assert client.get("/api/snapshots/9999").status_code == 403

    share(own["id"], "user", HOA)      # cá nhân
    share(own["id"], "group", "G01")   # Sales Team: Len, Phu, Mai
    assert [s["name"] for s in client.get("/api/snapshots").json()["shared_with_me"]] == ["Sales check"]
    assert client.get(f"/api/snapshots/{own['id']}").json()["can_delete"] is False
    assert client.delete(f"/api/snapshots/{own['id']}").status_code == 403   # người nhận không xóa được

    login(client, MAI)
    assert client.get(f"/api/snapshots/{own['id']}").status_code == 200
    login(client, YUKI)
    assert client.get(f"/api/snapshots/{own['id']}").status_code == 403


def test_leaving_group_loses_snapshot_access(client):
    login(client, PHU)
    own = client.post("/api/snapshots", json={}).json()
    share(own["id"], "group", "G01")
    with db.get_conn() as conn:
        conn.execute("DELETE FROM group_members WHERE group_id = 'G01' AND user_id = ?", (MAI,))
    login(client, MAI)
    assert client.get(f"/api/snapshots/{own['id']}").status_code == 403
    assert client.get("/api/snapshots").json()["shared_with_me"] == []


def test_owner_deletes_snapshot_and_shares(client):
    login(client, PHU)
    own = client.post("/api/snapshots", json={}).json()
    share(own["id"], "user", HOA)
    assert client.delete(f"/api/snapshots/{own['id']}").status_code == 200
    with db.get_conn() as conn:
        assert conn.execute("SELECT COUNT(*) FROM shares WHERE item_type = 'snapshot'").fetchone()[0] == 0
    login(client, HOA)
    assert client.get(f"/api/snapshots/{own['id']}").status_code == 403
    assert client.get("/api/snapshots").json()["shared_with_me"] == []
