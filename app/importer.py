"""Nạp CSV mẫu và xử lý file upload (chỉ System Administrator)."""
import csv
import io
import json
import sqlite3
from datetime import date, datetime

from . import config

ORDER_COLUMNS = [
    "order_id", "order_datetime", "customer_id", "region", "city",
    "product_category", "product_name", "sales_channel", "device",
    "payment_method", "discount_code", "unit_price", "quantity",
    "discount_amount", "order_value", "status",
]
REQUIRED_TEXT = [
    "order_id", "customer_id", "region", "city", "product_category",
    "product_name", "sales_channel", "device", "payment_method",
]
ORDER_STATUSES = {"completed", "cancelled", "refunded"}
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _read_csv(name: str) -> list[dict]:
    with open(config.DATA_DIR / name, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _bool(text: str) -> int:
    return 1 if text.strip().lower() in ("true", "1", "yes") else 0


def load_seed(conn: sqlite3.Connection) -> None:
    """Nạp toàn bộ CSV mẫu vào DB trống."""
    conn.executemany(
        f"INSERT INTO orders ({','.join(ORDER_COLUMNS)}) VALUES ({','.join('?' * len(ORDER_COLUMNS))})",
        [_order_tuple(r) for r in _read_csv("orders.csv")],
    )
    conn.executemany(
        "INSERT INTO customers VALUES (?,?,?,?,?,?,?,?)",
        [(r["customer_id"], r["full_name"], r["email"], r["signup_date"], r["region"],
          r["city"], r["segment"], r["acquisition_source"]) for r in _read_csv("customers.csv")],
    )
    conn.executemany(
        "INSERT INTO app_sessions VALUES (?,?,?,?,?,?,?)",
        [(r["session_id"], r["session_datetime"], r["user_id"], r["platform"],
          int(r["duration_seconds"]), int(r["pages_viewed"]), int(r["converted"]))
         for r in _read_csv("app_sessions.csv")],
    )
    conn.executemany(
        "INSERT INTO users VALUES (?,?,?,?,?)",
        [(r["user_id"], r["name"], r["email"] or None, r["system_role"], _bool(r["is_active"]))
         for r in _read_csv("users.csv")],
    )
    conn.executemany(
        "INSERT INTO groups VALUES (?,?,?)",
        [(r["group_id"], r["group_name"], r["group_owner_id"]) for r in _read_csv("groups.csv")],
    )
    conn.executemany(
        "INSERT INTO group_members VALUES (?,?,?)",
        [(r["group_id"], r["user_id"], r["group_role"]) for r in _read_csv("group_members.csv")],
    )
    conn.executemany(
        "INSERT INTO alert_rules (id, user_id, kpi, condition, threshold, is_active) VALUES (?,?,?,?,?,?)",
        [(r["rule_id"], r["owner_id"], r["kpi"], r["condition"].replace("goes ", ""),
          float(r["threshold"]), _bool(r["is_active"])) for r in _read_csv("alert_rules.csv")],
    )


def _order_tuple(r: dict) -> tuple:
    return (
        r["order_id"].strip(), r["order_datetime"].strip(), r["customer_id"].strip(),
        r["region"].strip(), r["city"].strip(), r["product_category"].strip(),
        r["product_name"].strip(), r["sales_channel"].strip(), r["device"].strip(),
        r["payment_method"].strip(), (r.get("discount_code") or "").strip() or None,
        float(r["unit_price"]), int(r["quantity"]), float(r["discount_amount"]),
        float(r["order_value"]), r["status"].strip(),
    )


# ---------------------------------------------------------------- upload

def _row_errors(r: dict, today: date) -> list[str]:
    """Trả danh sách lỗi của một dòng; rỗng nghĩa là dòng hợp lệ."""
    errors = []
    for col in REQUIRED_TEXT:
        if not (r.get(col) or "").strip():
            errors.append(f"{col} is blank")

    dt_text = (r.get("order_datetime") or "").strip()
    if not dt_text:
        errors.append("order_datetime is blank")
    else:
        try:
            dt = datetime.strptime(dt_text, DATETIME_FORMAT)
            if dt.date() > today:
                errors.append(f"order_datetime {dt_text} is in the future")
        except ValueError:
            errors.append(f"order_datetime '{dt_text}' is not in YYYY-MM-DD HH:MM:SS format")

    def number(col: str, integer: bool = False, positive: bool = False):
        text = (r.get(col) or "").strip()
        if not text:
            errors.append(f"{col} is blank")
            return
        try:
            value = int(text) if integer else float(text)
        except ValueError:
            errors.append(f"{col} '{text}' is not a number")
            return
        if value < 0 or (positive and value == 0):
            errors.append(f"{col} {text} must be {'greater than 0' if positive else '0 or more'}")

    number("unit_price")
    number("quantity", integer=True, positive=True)
    number("discount_amount")
    number("order_value")

    status = (r.get("status") or "").strip()
    if status not in ORDER_STATUSES:
        errors.append(f"status '{status}' must be one of completed, cancelled, refunded")
    return errors


def process_upload(conn: sqlite3.Connection, filename: str, content: bytes,
                   uploaded_by: str, today: date = config.TODAY) -> dict:
    """Kiểm tra và nạp file orders.

    - Thiếu cột hoặc không có dòng dữ liệu: từ chối cả file.
    - Dòng lỗi (kể cả ngày ở tương lai): bỏ dòng đó, nạp phần còn lại.
    - order_id lặp trong file: giữ dòng cuối.
    - Ghi đè theo order_id: đơn đã có được thay, đơn mới được thêm.
    """
    result = {
        "filename": filename, "status": "rejected", "rows_loaded": 0,
        "rows_skipped": 0, "skipped_rows": [], "duplicate_order_ids": [],
        "errors": [],
    }

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        result["errors"].append("The file is not a UTF-8 CSV file.")
        return _save_batch(conn, result, uploaded_by)

    reader = csv.DictReader(io.StringIO(text))
    header = [h.strip() for h in (reader.fieldnames or [])]
    missing = [c for c in ORDER_COLUMNS if c not in header]
    if missing:
        result["errors"].append("Missing required column(s): " + ", ".join(missing))
        return _save_batch(conn, result, uploaded_by)
    reader.fieldnames = header

    rows = [(i, r) for i, r in enumerate(reader, start=2)  # dòng 1 là tiêu đề
            if any((v or "").strip() for v in r.values())]
    if not rows:
        result["errors"].append("The file has a header row but no data rows.")
        return _save_batch(conn, result, uploaded_by)

    valid: dict[str, tuple] = {}
    seen_count: dict[str, int] = {}
    for line_no, r in rows:
        errors = _row_errors(r, today)
        if errors:
            result["skipped_rows"].append({
                "line": line_no, "order_id": (r.get("order_id") or "").strip(),
                "reasons": errors,
            })
            continue
        oid = r["order_id"].strip()
        seen_count[oid] = seen_count.get(oid, 0) + 1
        valid[oid] = _order_tuple(r)  # dòng sau ghi đè dòng trước: giữ dòng cuối

    result["duplicate_order_ids"] = sorted(oid for oid, n in seen_count.items() if n > 1)
    result["rows_skipped"] = len(result["skipped_rows"])
    result["rows_loaded"] = len(valid)
    result["status"] = "accepted"

    conn.executemany(
        f"INSERT OR REPLACE INTO orders ({','.join(ORDER_COLUMNS)}) "
        f"VALUES ({','.join('?' * len(ORDER_COLUMNS))})",
        list(valid.values()),
    )
    return _save_batch(conn, result, uploaded_by)


def _save_batch(conn: sqlite3.Connection, result: dict, uploaded_by: str) -> dict:
    cur = conn.execute(
        "INSERT INTO upload_batches (filename, uploaded_by, uploaded_at, status, row_count,"
        " skipped_count, skipped_rows_json, duplicate_ids_json, error_summary)"
        " VALUES (?,?,?,?,?,?,?,?,?)",
        (result["filename"], uploaded_by, datetime.now().strftime(DATETIME_FORMAT),
         result["status"], result["rows_loaded"], result["rows_skipped"],
         json.dumps(result["skipped_rows"]), json.dumps(result["duplicate_order_ids"]),
         "; ".join(result["errors"]) or None),
    )
    result["batch_id"] = cur.lastrowid
    return result
