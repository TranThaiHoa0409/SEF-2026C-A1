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


# Cảnh báo xét giá trị KPI của ngày đầy đủ gần nhất (hôm qua = 7 Nov).
ALERT_DAY_OFFSET = 1

# Email giả: lần gửi đầu ngay khi đến lượt (job chạy mỗi MAIL_POLL_SECONDS, dưới 1 phút),
# lỗi thì thử lại MAIL_RETRIES lần, cách nhau MAIL_RETRY_SECONDS.
MAIL_POLL_SECONDS = 10
MAIL_RETRIES = 3
MAIL_RETRY_SECONDS = 60
SCHEDULE_POLL_SECONDS = 30


def reports_dir() -> Path:
    """Thư mục chứa file PDF; test đổi bằng BIZBOARD_REPORTS."""
    path = Path(os.environ.get("BIZBOARD_REPORTS", ROOT / "reports"))
    path.mkdir(parents=True, exist_ok=True)
    return path
