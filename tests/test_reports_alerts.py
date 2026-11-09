"""Bước 4: báo cáo PDF, lịch, chia sẻ, rule cảnh báo, giao in-app và email giả."""
from datetime import date, datetime, timedelta

import pytest

from app import alerts, auth, config, db, notify, pdf, reports
from conftest import ADMIN, HOA, PHU, login

LEN, YUKI, MAI, BAO = "U03", "U05", "U06", "U07"
T0 = datetime(2026, 11, 8, 9, 0, 0)


def make_report(client, kpis=("Total Revenue",), period="last_7_days", **extra):
    return client.post("/api/reports", json={"kpis": list(kpis), "period_key": period, **extra})


def notes_of(conn, user_id):
    return conn.execute("SELECT * FROM notifications WHERE user_id = ? ORDER BY id", (user_id,)).fetchall()


# ------------------------------------------------------------------ báo cáo

def test_generate_report_and_download_pdf(client):
    login(client, PHU)
    r = make_report(client, kpis=["Total Revenue", "Total Sales"]).json()
    assert r["name"] == "Total Revenue, Total Sales, Last 7 days"
    assert [k["name"] for k in r["kpis"]] == ["Total Sales", "Total Revenue"]
    assert {k["name"]: k["value"] for k in r["kpis"]} == {"Total Sales": 421, "Total Revenue": 15641.04}
    assert r["period"]["dates_text"] == "1 to 7 Nov" and r["generated_at"]
    pdf_resp = client.get(f"/api/reports/{r['id']}/pdf")
    assert pdf_resp.status_code == 200 and pdf_resp.content[:4] == b"%PDF"
    lst = client.get("/api/reports").json()
    assert [x["name"] for x in lst["mine"]] == [r["name"]]


def test_default_and_custom_name(client):
    login(client, PHU)
    assert make_report(client).json()["name"] == "Total Revenue, Last 7 days"
    assert make_report(client, name="Weekly sales").json()["name"] == "Weekly sales"


def test_report_input_errors(client):
    login(client, PHU)
    r = make_report(client, kpis=[])
    assert r.status_code == 400 and "at least one KPI" in r.json()["detail"]
    assert make_report(client, period="last_year").status_code == 400
    assert make_report(client, kpis=["Profit"]).status_code == 400
    r = make_report(client, period="today")   # 8 Nov: không KPI nào có dữ liệu
    assert r.status_code == 422 and "No report was created" in r.json()["detail"]
    assert client.get("/api/reports").json()["mine"] == []


def test_partial_no_data_needs_confirmation(client):
    """Một số KPI không có dữ liệu: cần xác nhận "Generate without them".

    Kỳ 20–22 Sep (mất dữ liệu app) không chọn được vì báo cáo chỉ có 4 kỳ cố định tính từ 8 Nov,
    nên mô phỏng bằng cách xóa phiên app từ 1 Nov.
    """
    login(client, PHU)
    with db.get_conn() as conn:
        conn.execute("DELETE FROM app_sessions WHERE session_datetime >= '2026-11-01'")
    r = make_report(client, kpis=["Total Revenue", "Active Users", "Conversion Rate"])
    assert r.status_code == 409 and r.json()["missing"] == ["Active Users", "Conversion Rate"]
    assert client.get("/api/reports").json()["mine"] == []          # Cancel: không tạo gì
    ok = make_report(client, kpis=["Total Revenue", "Active Users", "Conversion Rate"], confirm_skip=True).json()
    assert [k["name"] for k in ok["kpis"]] == ["Total Revenue"]      # PDF không nhắc KPI bị bỏ


def test_pdf_failure_creates_nothing(client):
    login(client, PHU)
    pdf.pdf_engine["failing"] = True
    r = make_report(client)
    assert r.status_code == 500 and "try again" in r.json()["detail"].lower()
    assert client.get("/api/reports").json()["mine"] == []
    pdf.pdf_engine["failing"] = False
    assert make_report(client).status_code == 200


def test_report_does_not_change_after_upload(client):
    login(client, PHU)
    r = make_report(client, kpis=["Total Sales"]).json()
    login(client, ADMIN)
    with open(config.DATA_DIR / "upload_08_new_and_changed_orders.csv", "rb") as f:
        client.post("/api/uploads", files={"file": ("u8.csv", f, "text/csv")})
    login(client, PHU)
    assert client.get(f"/api/reports/{r['id']}").json()["kpis"][0]["value"] == 421


def test_only_owner_deletes_and_sees_report(client):
    login(client, PHU)
    r = make_report(client).json()
    login(client, HOA)
    assert client.get(f"/api/reports/{r['id']}").json()["detail"] == auth.NO_ACCESS
    assert client.get(f"/api/reports/{r['id']}/pdf").status_code == 403
    assert client.delete(f"/api/reports/{r['id']}").status_code == 403
    login(client, PHU)
    assert client.delete(f"/api/reports/{r['id']}").status_code == 200
    assert client.get("/api/reports").json()["mine"] == []


# ------------------------------------------------------------------ chia sẻ

def share(client, item_id, target_type, target_id, item_type="report"):
    return client.post("/api/shares", json={"item_type": item_type, "item_id": item_id,
                                             "target_type": target_type, "target_id": target_id})


def test_sharing_scenarios_from_readme(client):
    login(client, PHU)
    r = make_report(client).json()
    g = share(client, r["id"], "group", "G01")            # Sales Team
    assert g.status_code == 200 and sorted(g.json()["notified"]) == [LEN, MAI]
    assert share(client, r["id"], "user", HOA).status_code == 200
    no = share(client, r["id"], "group", "G02")           # Marketing: Phu không thuộc
    assert no.status_code == 403
    assert share(client, r["id"], "user", YUKI).status_code == 200
    assert share(client, r["id"], "user", HOA).status_code == 400   # đã chia sẻ
    assert share(client, r["id"], "user", "U08").status_code == 400  # Nam đã bị deactivate

    for uid in (LEN, MAI, HOA, YUKI):
        login(client, uid)
        assert [x["id"] for x in client.get("/api/reports").json()["shared_with_me"]] == [r["id"]]
        v = client.get(f"/api/reports/{r['id']}").json()
        assert v["is_owner"] is False and "shares" not in v
        assert client.get(f"/api/reports/{r['id']}/pdf").status_code == 200
        assert client.delete(f"/api/reports/{r['id']}").status_code == 403      # không xóa
        assert share(client, r["id"], "user", BAO).status_code == 403           # không chia sẻ lại
    login(client, BAO)
    assert client.get(f"/api/reports/{r['id']}").status_code == 403


def test_share_notifies_in_app_and_email(client):
    login(client, PHU)
    r = make_report(client).json()
    share(client, r["id"], "user", HOA)
    with db.get_conn() as conn:
        n = notes_of(conn, HOA)[-1]
        assert n["kind"] == "share" and "Phu shared" in n["title"] and n["email_status"] == "pending"
        mail = conn.execute("SELECT * FROM mailbox WHERE notification_id = ?", (n["id"],)).fetchone()
        assert mail["to_email"] == "hoa@bizboard.demo"


def test_revoke_and_leaving_group_remove_access(client):
    login(client, PHU)
    r = make_report(client).json()
    s = share(client, r["id"], "user", HOA).json()
    share(client, r["id"], "group", "G01")
    assert client.delete(f"/api/shares/{s['id']}").status_code == 200
    login(client, HOA)
    assert client.get(f"/api/reports/{r['id']}").status_code == 403
    with db.get_conn() as conn:
        conn.execute("DELETE FROM group_members WHERE group_id = 'G01' AND user_id = ?", (MAI,))
    login(client, MAI)
    assert client.get(f"/api/reports/{r['id']}").status_code == 403
    assert client.get("/api/reports").json()["shared_with_me"] == []
    login(client, LEN)
    assert client.delete(f"/api/shares/{s['id']}").status_code == 403


def test_deleting_report_removes_access(client):
    login(client, PHU)
    r = make_report(client).json()
    share(client, r["id"], "user", HOA)
    client.delete(f"/api/reports/{r['id']}")
    login(client, HOA)
    assert client.get("/api/reports").json()["shared_with_me"] == []


def test_snapshot_sharing(client):
    login(client, PHU)
    snap = client.post("/api/snapshots", json={}).json()
    assert share(client, snap["id"], "group", "G01", "snapshot").status_code == 200
    assert share(client, snap["id"], "group", "G02", "snapshot").status_code == 403
    login(client, MAI)
    assert client.get(f"/api/snapshots/{snap['id']}").status_code == 200
    assert share(client, snap["id"], "user", BAO, "snapshot").status_code == 403


def test_share_targets(client):
    login(client, PHU)
    t = client.get("/api/share-targets").json()
    assert [g["name"] for g in t["groups"]] == ["Sales Team"]
    assert "Phu" not in [u["name"] for u in t["users"]] and "Nam" not in [u["name"] for u in t["users"]]


# ------------------------------------------------------------------ rule cảnh báo

def test_r01_creates_exactly_two_alerts(conn):
    created = []
    d = date(2026, 6, 1)
    while d <= date(2026, 11, 7):
        for nid in alerts.check_rules(conn, d):
            n = conn.execute("SELECT * FROM notifications WHERE id = ?", (nid,)).fetchone()
            created.append((n["rule_id"], n["data_date"]))
        d += timedelta(days=1)
    r01 = [day for rule, day in created if rule == "R01"]
    assert r01 == ["2026-11-03", "2026-11-07"]     # 4 Nov không tạo thêm
    assert not [c for c in created if c[0] in ("R03", "R04", "R06")]


def test_alert_content(conn):
    alerts.check_rules(conn, date(2026, 11, 3))
    n = [x for x in notes_of(conn, HOA) if x["rule_id"] == "R01"][0]
    assert (n["kpi"], n["condition"], n["threshold"], n["value"]) == ("Total Revenue", "below", 1000.0, 662.5)
    assert "$662.50 on 3 Nov" in n["body"] and n["created_at"]


def test_no_data_skips_rule(conn):
    """20 Sep không có phiên app: rule Active Users bỏ qua, không tạo alert, không đổi trạng thái."""
    conn.execute("UPDATE alert_rules SET threshold = 0 WHERE id = 'R06'")   # luôn vượt nếu có dữ liệu
    assert all(conn.execute("SELECT rule_id FROM notifications WHERE id = ?", (i,)).fetchone()[0] != "R06"
               for i in alerts.check_rules(conn, date(2026, 9, 20)))
    assert conn.execute("SELECT is_triggered FROM alert_rules WHERE id = 'R06'").fetchone()[0] == 0


def test_turning_rule_off_and_on_alerts_again(client):
    login(client, HOA)
    with db.get_conn() as conn:
        alerts.check_rules(conn, date(2026, 11, 3))
        assert alerts.check_rules(conn, date(2026, 11, 4)) == []
    rule = {"kpi": "Total Revenue", "condition": "below", "threshold": 1000}
    client.put("/api/alert-rules/R01", json=rule | {"is_active": False})
    with db.get_conn() as conn:
        assert all(conn.execute("SELECT rule_id FROM notifications WHERE id = ?", (i,)).fetchone()[0] != "R01"
                   for i in alerts.check_rules(conn, date(2026, 11, 4)))
    client.put("/api/alert-rules/R01", json=rule | {"is_active": True})
    with db.get_conn() as conn:
        rules = [conn.execute("SELECT rule_id FROM notifications WHERE id = ?", (i,)).fetchone()[0]
                 for i in alerts.check_rules(conn, date(2026, 11, 4))]
    assert "R01" in rules


def test_rule_crud_and_validation(client):
    login(client, LEN)
    assert [r["id"] for r in client.get("/api/alert-rules").json()] == ["R04"]
    assert client.post("/api/alert-rules", json={"kpi": "Total Sales", "condition": "below", "threshold": ""}).status_code == 400
    assert client.post("/api/alert-rules", json={"kpi": "Total Sales", "condition": "below", "threshold": "abc"}).status_code == 400
    assert client.post("/api/alert-rules", json={"kpi": "Profit", "condition": "below", "threshold": 1}).status_code == 400
    a = client.post("/api/alert-rules", json={"kpi": "Total Sales", "condition": "below", "threshold": 50}).json()
    b = client.post("/api/alert-rules", json={"kpi": "Total Sales", "condition": "above", "threshold": 100}).json()
    assert a["id"] == "R07" and b["id"] == "R08" and a["text"] == "Total Sales goes below 50"
    assert client.delete(f"/api/alert-rules/{a['id']}").status_code == 200
    assert [r["id"] for r in client.get("/api/alert-rules").json()] == ["R04", "R08"]
    login(client, HOA)
    assert client.delete("/api/alert-rules/R08").status_code == 403
    assert client.put("/api/alert-rules/R04", json={"kpi": "New Customers", "condition": "below",
                                                    "threshold": 1}).status_code == 403


def test_refresh_checks_rules(client):
    from app import scheduler
    scheduler.refresh("test")   # ngày kiểm tra mặc định = 7 Nov
    with db.get_conn() as conn:
        rules = {n["rule_id"] for n in conn.execute("SELECT rule_id FROM notifications")}
    assert rules == {"R01", "R05"}


# ------------------------------------------------------------------ giao và email giả

def test_bao_without_email_gets_in_app_only(conn):
    conn.execute("INSERT INTO alert_rules (id, user_id, kpi, condition, threshold, is_active) "
                 "VALUES ('R90', ?, 'Total Revenue', 'below', 1000, 1)", (BAO,))
    alerts.check_rules(conn, date(2026, 11, 3))
    n = notes_of(conn, BAO)[0]
    assert n["email_status"].startswith("in-app only")
    assert conn.execute("SELECT COUNT(*) FROM mailbox WHERE to_user_id = ?", (BAO,)).fetchone()[0] == 0


def test_email_switch_off(conn):
    notify.save_settings(conn, HOA, email_on_alert=False, email_on_share=True)
    alerts.check_rules(conn, date(2026, 11, 3))
    n = [x for x in notes_of(conn, HOA) if x["rule_id"] == "R01"][0]
    assert n["email_status"] == "in-app only (email turned off)"
    assert conn.execute("SELECT COUNT(*) FROM mailbox WHERE to_user_id = ?", (HOA,)).fetchone()[0] == 0


def test_email_sent_within_one_minute(conn, monkeypatch):
    monkeypatch.setattr(notify, "now", lambda: T0)
    alerts.check_rules(conn, date(2026, 11, 3))
    notify.process_mailbox(conn, T0 + timedelta(seconds=config.MAIL_POLL_SECONDS))
    mail = conn.execute("SELECT * FROM mailbox WHERE to_user_id = ?", (HOA,)).fetchone()
    assert mail["status"] == "sent" and mail["attempt"] == 1
    assert datetime.strptime(mail["sent_at"], "%Y-%m-%d %H:%M:%S") - T0 < timedelta(minutes=1)
    assert notes_of(conn, HOA)[0]["email_status"] == "sent"


def test_email_retries_three_times_then_not_delivered(conn, monkeypatch):
    monkeypatch.setattr(notify, "now", lambda: T0)
    alerts.check_rules(conn, date(2026, 11, 3))
    notify.mail_server["failing"] = True
    t = T0
    for _ in range(10):   # chạy job đủ lâu, mỗi 10 giây
        notify.process_mailbox(conn, t)
        t += timedelta(seconds=10)
    mail = conn.execute("SELECT * FROM mailbox WHERE to_user_id = ?", (HOA,)).fetchone()
    assert mail["status"] == "pending" and mail["attempt"] == 2
    for _ in range(30):
        notify.process_mailbox(conn, t)
        t += timedelta(seconds=10)
    import json
    mail = conn.execute("SELECT * FROM mailbox WHERE to_user_id = ?", (HOA,)).fetchone()
    tries = [datetime.strptime(a["at"], "%Y-%m-%d %H:%M:%S") for a in json.loads(mail["attempts_json"])]
    assert mail["status"] == "failed" and mail["attempt"] == 4      # lần đầu + 3 lần thử lại
    assert [b - a for a, b in zip(tries, tries[1:])] == [timedelta(minutes=1)] * 3
    n = notes_of(conn, HOA)[0]
    assert n["email_status"] == notify.NOT_DELIVERED                 # alert vẫn còn trong app
    assert conn.execute("SELECT COUNT(*) FROM activity_log WHERE action = 'email_failed'").fetchone()[0] >= 1


def test_retry_stops_when_mail_recovers(conn, monkeypatch):
    monkeypatch.setattr(notify, "now", lambda: T0)
    alerts.check_rules(conn, date(2026, 11, 3))
    notify.mail_server["failing"] = True
    notify.process_mailbox(conn, T0)
    notify.mail_server["failing"] = False
    notify.process_mailbox(conn, T0 + timedelta(minutes=1))
    mail = conn.execute("SELECT * FROM mailbox WHERE to_user_id = ?", (HOA,)).fetchone()
    assert mail["status"] == "sent" and mail["attempt"] == 2


def test_notifications_unread_first_and_mark_read(client):
    with db.get_conn() as conn:
        alerts.check_rules(conn, date(2026, 11, 1))   # R02
        alerts.check_rules(conn, date(2026, 11, 3))   # R01
    login(client, HOA)
    data = client.get("/api/notifications").json()
    assert data["unread"] == 2
    first = data["items"][-1]["id"]
    assert client.post(f"/api/notifications/{first}/read").status_code == 200
    items = client.get("/api/notifications").json()["items"]
    assert items[-1]["id"] == first and items[-1]["is_read"]
    login(client, PHU)
    assert client.post(f"/api/notifications/{first}/read").status_code == 403


def test_notification_settings_default_on(client):
    login(client, BAO)
    s = client.get("/api/notification-settings").json()
    assert s["email_on_alert"] and s["email_on_share"] and not s["has_email"]
    s = client.put("/api/notification-settings", json={"email_on_alert": False, "email_on_share": True}).json()
    assert not s["email_on_alert"]


# ------------------------------------------------------------------ báo cáo định kỳ

def test_scheduled_report_runs_and_notifies(client):
    login(client, PHU)
    s = client.post("/api/schedules", json={"kpis": ["Total Sales"], "period_key": "last_7_days",
                                            "frequency": "weekly", "first_run": "2026-11-09T08:00"}).json()
    assert s["next_run"] == "2026-11-09 08:00:00" and s["name"] == "Total Sales, Last 7 days"
    done = reports.run_due_schedules(datetime(2026, 11, 9, 8, 0, 30))
    assert done[0]["report_id"]
    lst = client.get("/api/reports").json()["mine"]
    assert lst[0]["name"] == "Total Sales, Last 7 days"
    assert client.get("/api/schedules").json()[0]["next_run"] == "2026-11-16 08:00:00"
    with db.get_conn() as conn:
        assert notes_of(conn, PHU)[-1]["title"].startswith("Scheduled report ready")
    assert reports.run_due_schedules(datetime(2026, 11, 9, 9, 0)) == []


def test_scheduled_report_failure_notifies(client):
    login(client, PHU)
    client.post("/api/schedules", json={"kpis": ["Total Sales"], "period_key": "today",
                                        "frequency": "daily", "first_run": "2026-11-09T08:00"})
    done = reports.run_due_schedules(datetime(2026, 11, 9, 8, 1))
    assert "error" in done[0]
    with db.get_conn() as conn:
        assert notes_of(conn, PHU)[-1]["title"].startswith("Scheduled report failed")
    assert client.get("/api/schedules").json()[0]["last_error"]


def test_schedule_edit_cancel_and_validation(client):
    login(client, PHU)
    bad = client.post("/api/schedules", json={"kpis": [], "period_key": "last_7_days",
                                              "frequency": "weekly", "first_run": "2026-11-09T08:00"})
    assert bad.status_code == 400
    assert client.post("/api/schedules", json={"kpis": ["Total Sales"], "frequency": "hourly",
                                               "first_run": "2026-11-09T08:00"}).status_code == 400
    s = client.post("/api/schedules", json={"kpis": ["Total Sales"], "frequency": "monthly",
                                            "first_run": "2026-01-31T08:00"}).json()
    upd = client.put(f"/api/schedules/{s['id']}", json={"kpis": ["Total Revenue"], "frequency": "monthly",
                                                        "first_run": "2026-01-31T08:00", "active": False}).json()
    assert upd["kpis"] == ["Total Revenue"] and not upd["active"]
    login(client, HOA)
    assert client.delete(f"/api/schedules/{s['id']}").status_code == 403
    login(client, PHU)
    assert client.delete(f"/api/schedules/{s['id']}").status_code == 200
    assert reports._next_run(datetime(2026, 1, 31, 8), "monthly") == datetime(2026, 2, 28, 8)


# ------------------------------------------------------------------ công cụ demo

def test_dev_tools_admin_only(client):
    login(client, HOA)
    assert client.get("/api/dev/mailbox").status_code == 403
    login(client, ADMIN)
    r = client.post("/api/dev/replay-alerts", json={"start": "2026-11-01", "end": "2026-11-07"}).json()
    r01 = [c["date"] for c in r["created"] if c["rule_id"] == "R01"]
    assert r01 == ["2026-11-03", "2026-11-07"]
    assert client.put("/api/dev/mail-failure", json={"failing": True}).json()["mail_failing"]
    assert client.get("/api/dev/mailbox").json()["mail_failing"]
    notify.mail_server["failing"] = False


@pytest.fixture(autouse=True)
def _reset_flags():
    yield
    notify.mail_server["failing"] = False
    pdf.pdf_engine["failing"] = False
