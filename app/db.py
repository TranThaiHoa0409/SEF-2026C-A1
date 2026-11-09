"""Kết nối SQLite và tạo bảng."""
import sqlite3
from contextlib import contextmanager

from . import config

SCHEMA = """
-- Dữ liệu kinh doanh (nạp từ CSV)
CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    order_datetime TEXT NOT NULL,
    customer_id TEXT NOT NULL,
    region TEXT NOT NULL,
    city TEXT NOT NULL,
    product_category TEXT NOT NULL,
    product_name TEXT NOT NULL,
    sales_channel TEXT NOT NULL,
    device TEXT NOT NULL,
    payment_method TEXT NOT NULL,
    discount_code TEXT,
    unit_price REAL NOT NULL,
    quantity INTEGER NOT NULL,
    discount_amount REAL NOT NULL,
    order_value REAL NOT NULL,
    status TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_orders_dt ON orders(order_datetime);
CREATE INDEX IF NOT EXISTS ix_orders_customer ON orders(customer_id);

CREATE TABLE IF NOT EXISTS customers (
    customer_id TEXT PRIMARY KEY,
    full_name TEXT,
    email TEXT,
    signup_date TEXT NOT NULL,
    region TEXT,
    city TEXT,
    segment TEXT,
    acquisition_source TEXT
);
CREATE INDEX IF NOT EXISTS ix_customers_signup ON customers(signup_date);

CREATE TABLE IF NOT EXISTS app_sessions (
    session_id TEXT PRIMARY KEY,
    session_datetime TEXT NOT NULL,
    user_id TEXT NOT NULL,
    platform TEXT,
    duration_seconds INTEGER,
    pages_viewed INTEGER,
    converted INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_sessions_dt ON app_sessions(session_datetime);

-- Người dùng, nhóm
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    system_role TEXT NOT NULL,
    is_active INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS groups (
    group_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    owner_id TEXT NOT NULL REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS group_members (
    group_id TEXT NOT NULL REFERENCES groups(group_id),
    user_id TEXT NOT NULL REFERENCES users(id),
    role TEXT NOT NULL,
    PRIMARY KEY (group_id, user_id)
);

-- Phiên đăng nhập (hết sau 30 phút không hoạt động)
CREATE TABLE IF NOT EXISTS auth_sessions (
    token TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    last_seen TEXT NOT NULL
);

-- Upload và refresh
CREATE TABLE IF NOT EXISTS upload_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    uploaded_by TEXT NOT NULL REFERENCES users(id),
    uploaded_at TEXT NOT NULL,
    status TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    skipped_count INTEGER NOT NULL,
    skipped_rows_json TEXT NOT NULL,
    duplicate_ids_json TEXT NOT NULL,
    error_summary TEXT
);
CREATE TABLE IF NOT EXISTS refresh_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    refreshed_at TEXT NOT NULL,
    reason TEXT NOT NULL
);

-- Dashboard, snapshot, báo cáo, chia sẻ, ghi chú
CREATE TABLE IF NOT EXISTS dashboard_prefs (
    user_id TEXT PRIMARY KEY REFERENCES users(id),
    widget_ids_json TEXT NOT NULL,
    period_key TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id TEXT NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    captured_at TEXT NOT NULL,
    data_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id TEXT NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    kpis_json TEXT NOT NULL,
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    period_label TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    pdf_path TEXT,
    schedule_id INTEGER
);
CREATE TABLE IF NOT EXISTS report_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id TEXT NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    kpis_json TEXT NOT NULL,
    period_key TEXT NOT NULL,
    frequency TEXT NOT NULL,
    next_run TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    last_error TEXT
);
CREATE TABLE IF NOT EXISTS shares (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_type TEXT NOT NULL,
    item_id INTEGER NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL REFERENCES reports(id),
    author_id TEXT NOT NULL REFERENCES users(id),
    body TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT
);

-- Cảnh báo và thông báo
CREATE TABLE IF NOT EXISTS alert_rules (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    kpi TEXT NOT NULL,
    condition TEXT NOT NULL,
    threshold REAL NOT NULL,
    is_active INTEGER NOT NULL,
    is_triggered INTEGER NOT NULL DEFAULT 0
);
-- Danh sách thông báo trong app: cảnh báo (kind = alert), chia sẻ (share), báo cáo định kỳ (report).
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL REFERENCES users(id),
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    rule_id TEXT,
    kpi TEXT,
    condition TEXT,
    threshold REAL,
    value REAL,
    data_date TEXT,
    link TEXT,
    created_at TEXT NOT NULL,
    is_read INTEGER NOT NULL DEFAULT 0,
    email_status TEXT
);
CREATE TABLE IF NOT EXISTS notification_settings (
    user_id TEXT PRIMARY KEY REFERENCES users(id),
    email_on_alert INTEGER NOT NULL DEFAULT 1,
    email_on_share INTEGER NOT NULL DEFAULT 1
);
-- Hộp thư giả thay cho email thật.
CREATE TABLE IF NOT EXISTS mailbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notification_id INTEGER REFERENCES notifications(id),
    to_user_id TEXT NOT NULL REFERENCES users(id),
    to_email TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    attempt INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    queued_at TEXT NOT NULL,
    next_attempt_at TEXT NOT NULL,
    attempts_json TEXT NOT NULL DEFAULT '[]',
    sent_at TEXT
);
CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_id TEXT NOT NULL,
    action TEXT NOT NULL,
    target TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_conn():
    """Mở kết nối, commit khi xong, rollback khi lỗi."""
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# Bảng đã đổi cấu trúc từ bước 4. Bảng cũ còn trống thì tạo lại; còn dữ liệu thì báo lỗi rõ.
_REBUILD = {"reports": "period_label", "report_schedules": "last_error", "mailbox": "next_attempt_at"}


def _upgrade(conn: sqlite3.Connection) -> None:
    conn.execute("DROP TABLE IF EXISTS alerts")   # thay bằng notifications, chưa từng có dữ liệu
    for table, column in _REBUILD.items():
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
        if cols and column not in cols:
            if conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]:
                raise RuntimeError(f"Table {table} is outdated. Delete {config.db_path()} and start again.")
            conn.execute(f"DROP TABLE {table}")


def init_db() -> None:
    """Tạo bảng và nạp CSV mẫu nếu DB còn trống."""
    from . import importer

    with get_conn() as conn:
        _upgrade(conn)
        conn.executescript(SCHEMA)
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            importer.load_seed(conn)
