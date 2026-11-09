import os
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["BIZBOARD_NO_SCHEDULER"] = "1"

from app import config, db  # noqa: E402


@pytest.fixture(scope="session")
def seeded_db(tmp_path_factory) -> Path:
    """Nạp CSV mẫu một lần, mỗi test chép ra bản riêng."""
    path = tmp_path_factory.mktemp("seed") / "seed.db"
    os.environ["BIZBOARD_DB"] = str(path)
    db.init_db()
    return path


@pytest.fixture(autouse=True)
def fresh_db(seeded_db, tmp_path, monkeypatch):
    path = tmp_path / "bizboard.db"
    shutil.copy(seeded_db, path)
    monkeypatch.setenv("BIZBOARD_DB", str(path))
    monkeypatch.setenv("BIZBOARD_REPORTS", str(tmp_path / "reports"))
    from app import notify, pdf
    monkeypatch.setitem(notify.mail_server, "failing", False)
    monkeypatch.setitem(pdf.pdf_engine, "failing", False)
    return path


@pytest.fixture
def conn(fresh_db):
    c = db.connect()
    yield c
    c.close()


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c


def login(client, user_id: str):
    r = client.post("/api/auth/login", json={"user_id": user_id})
    assert r.status_code == 200, r.text
    return r.json()


ADMIN, HOA, PHU, NAM = "U01", "U02", "U04", "U08"
DATA = config.DATA_DIR
