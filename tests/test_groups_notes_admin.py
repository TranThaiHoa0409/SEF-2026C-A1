"""Bước 5: nhóm, ghi chú, trang System Administrator."""
from app import auth, db
from conftest import ADMIN, HOA, PHU, login

LEN, YUKI, MAI, BAO, NAM = "U03", "U05", "U06", "U07", "U08"


def phu_report_shared(client):
    """Phu tạo báo cáo, chia sẻ cho Sales Team và riêng cho Hoa (README mục 5)."""
    login(client, PHU)
    r = client.post("/api/reports", json={"kpis": ["Total Revenue"], "period_key": "last_7_days"}).json()
    for target_type, target_id in (("group", "G01"), ("user", HOA)):
        client.post("/api/shares", json={"item_type": "report", "item_id": r["id"],
                                         "target_type": target_type, "target_id": target_id})
    return r["id"]


def note(client, report_id, body="Revenue dipped on 3 Nov."):
    return client.post(f"/api/reports/{report_id}/notes", json={"body": body})


def activity(conn):
    return [(a["action"], a["target"]) for a in conn.execute("SELECT * FROM activity_log ORDER BY id")]


# ------------------------------------------------------------------ ghi chú

def test_note_rights_from_readme(client):
    rid = phu_report_shared(client)
    assert note(client, rid, "Owner note").status_code == 200                 # chủ báo cáo
    for uid in (LEN, MAI):                                                    # nhận qua nhóm: viết được
        login(client, uid)
        assert client.get(f"/api/reports/{rid}/notes").json()["can_write"] is True
        assert note(client, rid, f"Note from {uid}").status_code == 200
    login(client, HOA)                                                        # nhận cá nhân: chỉ đọc
    lst = client.get(f"/api/reports/{rid}/notes").json()
    assert lst["can_write"] is False and len(lst["items"]) == 3
    assert client.get(f"/api/reports/{rid}").json()["can_write_notes"] is False
    r = note(client, rid)
    assert r.status_code == 403 and r.json()["detail"] == auth.NO_ACCESS
    login(client, YUKI)                                                       # không có quyền
    assert client.get(f"/api/reports/{rid}/notes").status_code == 403


def test_note_shows_author_and_time(client):
    rid = phu_report_shared(client)
    login(client, LEN)
    n = note(client, rid).json()
    assert n["author_name"] == "Len" and n["created_at"]


def test_author_edits_and_deletes_own_note(client):
    rid = phu_report_shared(client)
    login(client, LEN)
    n = note(client, rid).json()
    upd = client.put(f"/api/reports/{rid}/notes/{n['id']}", json={"body": "Edited"}).json()
    assert upd["body"] == "Edited" and upd["updated_at"]
    login(client, MAI)
    assert client.put(f"/api/reports/{rid}/notes/{n['id']}", json={"body": "x"}).status_code == 403
    assert client.delete(f"/api/reports/{rid}/notes/{n['id']}").status_code == 403
    login(client, LEN)
    assert client.delete(f"/api/reports/{rid}/notes/{n['id']}").status_code == 200


def test_report_owner_and_admin_delete_any_note(client):
    rid = phu_report_shared(client)
    login(client, LEN)
    a = note(client, rid).json()
    login(client, MAI)
    b = note(client, rid).json()
    login(client, PHU)
    assert client.put(f"/api/reports/{rid}/notes/{a['id']}", json={"body": "x"}).status_code == 403  # không sửa
    assert client.delete(f"/api/reports/{rid}/notes/{a['id']}").status_code == 200
    login(client, ADMIN)
    assert [n["id"] for n in client.get("/api/admin/notes").json()] == [b["id"]]
    assert client.delete(f"/api/reports/{rid}/notes/{b['id']}").status_code == 200
    with db.get_conn() as conn:
        assert [x[0] for x in activity(conn)].count("note_deleted") == 2


def test_note_validation(client):
    rid = phu_report_shared(client)
    assert note(client, rid, "   ").status_code == 400
    assert note(client, rid, "x" * 1001).status_code == 400


def test_mai_leaves_sales_team_loses_report_and_notes(client):
    rid = phu_report_shared(client)
    login(client, MAI)
    note(client, rid, "Mai was here")
    assert client.post("/api/groups/G01/leave").status_code == 200
    assert client.get(f"/api/reports/{rid}").status_code == 403
    assert client.get(f"/api/reports/{rid}/notes").status_code == 403
    assert note(client, rid).status_code == 403
    assert client.get("/api/reports").json()["shared_with_me"] == []
    login(client, PHU)
    assert [n["author_name"] for n in client.get(f"/api/reports/{rid}/notes").json()["items"]] == ["Mai"]  # ghi chú cũ còn


# ------------------------------------------------------------------ nhóm

def test_create_group_makes_owner(client):
    login(client, BAO)
    g = client.post("/api/groups", json={"name": "Support"}).json()
    assert g["group_id"] == "G04" and g["owner_id"] == BAO
    assert g["members"] == [{"user_id": BAO, "name": "Bao", "email": None, "role": "Group Owner", "is_active": 1}]
    assert client.post("/api/groups", json={"name": "  "}).status_code == 400
    assert [x["name"] for x in client.get("/api/groups").json()] == ["Marketing", "Support"]


def test_owner_adds_and_removes_members_without_invitation(client):
    login(client, LEN)
    found = client.get("/api/groups/G01/candidates", params={"q": "hoa"}).json()
    assert [u["name"] for u in found] == ["Hoa"]
    assert [u["name"] for u in client.get("/api/groups/G01/candidates", params={"q": "yuki@"}).json()] == ["Yuki"]
    assert "Admin An" not in [u["name"] for u in client.get("/api/groups/G01/candidates").json()]
    g = client.post("/api/groups/G01/members", json={"user_id": HOA}).json()
    assert HOA in g["member_ids"]
    assert client.post("/api/groups/G01/members", json={"user_id": HOA}).status_code == 400
    assert client.post("/api/groups/G01/members", json={"user_id": NAM}).status_code == 400
    g = client.delete(f"/api/groups/G01/members/{PHU}").json()
    assert PHU not in g["member_ids"]
    with db.get_conn() as conn:
        acts = activity(conn)
    assert ("member_added", "Hoa to Sales Team (G01)") in acts
    assert ("member_removed", "Phu from Sales Team (G01)") in acts


def test_removed_member_loses_access(client):
    rid = phu_report_shared(client)
    login(client, LEN)
    client.delete(f"/api/groups/G01/members/{MAI}")
    login(client, MAI)
    assert client.get(f"/api/reports/{rid}").status_code == 403


def test_member_cannot_manage_and_outsider_cannot_see(client):
    login(client, PHU)
    assert client.get("/api/groups/G01").json()["can_manage"] is False
    assert client.post("/api/groups/G01/members", json={"user_id": HOA}).status_code == 403
    assert client.put("/api/groups/G01", json={"name": "X"}).status_code == 403
    assert client.delete("/api/groups/G01").status_code == 403
    r = client.get("/api/groups/G02")   # Marketing: Phu không thuộc
    assert r.status_code == 403 and r.json()["detail"] == auth.NO_ACCESS
    assert [g["name"] for g in client.get("/api/groups").json()] == ["Sales Team"]


def test_owner_must_hand_over_before_leaving(client):
    login(client, LEN)
    r = client.post("/api/groups/G01/leave")
    assert r.status_code == 400 and "Hand the group" in r.json()["detail"]
    assert client.put("/api/groups/G01/owner", json={"user_id": HOA}).status_code == 400   # không phải thành viên
    g = client.put("/api/groups/G01/owner", json={"user_id": PHU}).json()
    assert g["owner_id"] == PHU
    assert {m["user_id"]: m["role"] for m in g["members"]}[LEN] == "Member"
    assert client.post("/api/groups/G01/leave").status_code == 200
    login(client, PHU)
    assert client.get("/api/groups/G01").json()["can_manage"] is True


def test_owner_cannot_be_removed(client):
    login(client, LEN)
    assert client.delete(f"/api/groups/G01/members/{LEN}").status_code == 400


def test_rename_and_delete_group_keeps_reports(client):
    rid = phu_report_shared(client)
    login(client, PHU)
    snap = client.post("/api/snapshots", json={}).json()
    client.post("/api/shares", json={"item_type": "snapshot", "item_id": snap["id"],
                                     "target_type": "group", "target_id": "G01"})
    login(client, LEN)
    assert client.put("/api/groups/G01", json={"name": "Sales"}).json()["name"] == "Sales"
    assert client.delete("/api/groups/G01").status_code == 200
    login(client, MAI)
    assert client.get(f"/api/reports/{rid}").status_code == 403
    assert client.get(f"/api/snapshots/{snap['id']}").status_code == 403
    login(client, PHU)
    assert client.get(f"/api/reports/{rid}").status_code == 200     # báo cáo không bị xóa
    assert [s["target_name"] for s in client.get(f"/api/reports/{rid}").json()["shares"]] == ["Hoa"]
    login(client, HOA)
    assert client.get(f"/api/reports/{rid}").status_code == 200     # chia sẻ cá nhân giữ nguyên


# ------------------------------------------------------------------ System Administrator

def test_admin_pages_admin_only(client):
    login(client, HOA)
    for path in ("/api/admin/users", "/api/admin/groups", "/api/admin/notes", "/api/admin/activity"):
        r = client.get(path)
        assert r.status_code == 403 and r.json()["detail"] == auth.NO_ACCESS


def test_admin_sees_and_edits_every_group(client):
    login(client, ADMIN)
    assert [g["name"] for g in client.get("/api/admin/groups").json()] == ["Management", "Marketing", "Sales Team"]
    assert client.get("/api/groups/G02").json()["can_manage"] is True
    assert client.post("/api/groups/G02/members", json={"user_id": HOA}).status_code == 200
    assert client.delete(f"/api/groups/G02/members/{BAO}").status_code == 200
    g = client.put("/api/groups/G02/owner", json={"user_id": LEN}).json()   # Admin chọn được người ngoài nhóm
    assert g["owner_id"] == LEN and LEN in g["member_ids"]
    assert client.delete("/api/groups/G03").status_code == 200
    log = client.get("/api/admin/activity").json()
    assert {a["action"] for a in log} >= {"member_added", "member_removed", "owner_changed", "group_deleted"}
    assert all(a["actor_name"] == "Admin An" for a in log)


def test_admin_deactivates_user(client):
    login(client, MAI)
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as admin_client:
        login(admin_client, ADMIN)
        assert admin_client.post(f"/api/admin/users/{MAI}/deactivate").status_code == 200
        assert admin_client.post(f"/api/admin/users/{MAI}/deactivate").status_code == 400
        assert admin_client.post(f"/api/admin/users/{ADMIN}/deactivate").status_code == 400
        users = {u["id"]: u for u in admin_client.get("/api/admin/users").json()}
        assert users[MAI]["is_active"] is False
    assert client.get("/api/auth/me").status_code == 401                 # phiên đang mở bị đóng
    assert client.post("/api/auth/login", json={"user_id": MAI}).status_code == 403
    login(client, LEN)
    assert MAI not in [u["id"] for u in client.get("/api/groups/G01/candidates").json()]
