"""Upload CSV: các file upload_01 đến upload_08 trong data/."""
from app import auth, scheduler
from conftest import ADMIN, DATA, PHU, login


def upload(client, name: str):
    with open(DATA / name, "rb") as f:
        return client.post("/api/uploads", files={"file": (name, f, "text/csv")})


def day_totals(client, day: str = "2026-11-05"):
    data = client.get("/api/kpis", params={"start": day, "end": day}).json()
    v = {k["name"]: k["value"] for k in data["kpis"]}
    return v["Total Sales"], v["Total Revenue"]


def test_only_admin_can_upload(client):
    login(client, PHU)
    r = upload(client, "upload_01_valid_orders.csv")
    assert r.status_code == 403
    assert r.json()["detail"] == auth.NO_ACCESS
    assert client.get("/api/uploads").status_code == 403


def test_upload_01_same_data_no_double_count(client):
    login(client, ADMIN)
    assert day_totals(client) == (79, 2985.05)
    r = upload(client, "upload_01_valid_orders.csv").json()
    assert r["status"] == "accepted" and r["rows_loaded"] == 40 and r["rows_skipped"] == 0
    assert scheduler.last_refresh()["reason"] == "upload upload_01_valid_orders.csv"
    assert day_totals(client) == (79, 2985.05)


def test_upload_08_changes_dashboard_right_away(client):
    login(client, ADMIN)
    r = upload(client, "upload_08_new_and_changed_orders.csv").json()
    assert r["status"] == "accepted" and r["rows_loaded"] == 15
    assert r["refreshed_at"]
    assert day_totals(client) == (88, 3326.19)
    week = client.get("/api/kpis?period=last_7_days").json()
    v = {k["name"]: k["value"] for k in week["kpis"]}
    assert (v["Total Sales"], v["Total Revenue"]) == (430, 15982.18)


def test_upload_02_missing_column_rejected(client):
    login(client, ADMIN)
    r = upload(client, "upload_02_missing_column_order_value.csv").json()
    assert r["status"] == "rejected" and r["rows_loaded"] == 0
    assert "order_value" in r["errors"][0]
    assert day_totals(client) == (79, 2985.05)


def test_upload_05_header_only_rejected(client):
    login(client, ADMIN)
    r = upload(client, "upload_05_empty_header_only.csv").json()
    assert r["status"] == "rejected"
    assert "no data rows" in r["errors"][0]


def test_upload_03_bad_dates_skipped(client):
    login(client, ADMIN)
    r = upload(client, "upload_03_bad_dates.csv").json()
    assert r["status"] == "accepted"
    assert (r["rows_loaded"], r["rows_skipped"]) == (17, 3)
    assert [s["order_id"] for s in r["skipped_rows"]] == ["O12724", "O12685", "O12694"]
    assert [s["line"] for s in r["skipped_rows"]] == [4, 9, 13]


def test_upload_04_duplicates_keep_last(client):
    login(client, ADMIN)
    r = upload(client, "upload_04_duplicate_order_ids.csv").json()
    assert r["rows_loaded"] == 15 and r["rows_skipped"] == 0
    assert r["duplicate_order_ids"] == ["O12696", "O12701", "O12712", "O12719", "O12724"]
    assert day_totals(client) == (79, 2985.05)   # không tính đôi doanh thu


def test_upload_06_bad_values_skipped(client):
    login(client, ADMIN)
    r = upload(client, "upload_06_negative_blank_and_text_values.csv").json()
    assert (r["rows_loaded"], r["rows_skipped"]) == (15, 5)
    reasons = {s["order_id"]: " ".join(s["reasons"]) for s in r["skipped_rows"]}
    assert "order_value -19.5" in reasons["O12719"]
    assert "'abc' is not a number" in reasons["O12712"]
    assert "customer_id is blank" in reasons["O12728"]
    assert "quantity 'two'" in reasons["O12677"]
    assert "order_value is blank" in reasons["O12723"]


def test_upload_07_future_dates_skipped(client):
    login(client, ADMIN)
    r = upload(client, "upload_07_dates_in_the_future.csv").json()
    assert r["status"] == "accepted"
    assert (r["rows_loaded"], r["rows_skipped"]) == (0, 15)
    assert all("in the future" in s["reasons"][0] for s in r["skipped_rows"])


def test_upload_history_for_admin(client):
    login(client, ADMIN)
    upload(client, "upload_02_missing_column_order_value.csv")
    upload(client, "upload_03_bad_dates.csv")
    history = client.get("/api/uploads").json()
    assert [(h["filename"], h["status"], h["row_count"], h["skipped_count"]) for h in history] == [
        ("upload_03_bad_dates.csv", "accepted", 17, 3),
        ("upload_02_missing_column_order_value.csv", "rejected", 0, 0),
    ]
    assert history[0]["uploaded_by_name"] == "Admin An"
