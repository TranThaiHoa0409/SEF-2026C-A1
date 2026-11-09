"""Cấu hình chung của prototype."""
import os
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
STATIC_DIR = ROOT / "static"

# "Hôm nay" cố định để Last 7 days = 1 đến 7 Nov (xem data/README.md).
TODAY = date(2026, 11, 8)

SESSION_TIMEOUT_MINUTES = 30
REFRESH_INTERVAL_MINUTES = 5


def db_path() -> Path:
    """Đường dẫn file SQLite; test đổi bằng biến môi trường BIZBOARD_DB."""
    return Path(os.environ.get("BIZBOARD_DB", ROOT / "bizboard.db"))


def scheduler_enabled() -> bool:
    return os.environ.get("BIZBOARD_NO_SCHEDULER") != "1"
