"""Module KPI duy nhất. Dashboard, analytics, báo cáo và cảnh báo đều gọi module này.

Quy tắc:
- Chỉ đơn status = 'completed' được tính.
- Total Sales đếm số đơn.
- Không có dữ liệu: value = None, status = "no_data", kèm thông báo nêu rõ kỳ và bộ lọc.
- Bộ lọc không áp dụng được cho KPI: status = "not_applicable", không trả số.
"""
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import date, timedelta
from typing import Optional

from . import config

# ------------------------------------------------------------------ định nghĩa

@dataclass(frozen=True)
class KpiDef:
    name: str
    group: str      # Sales, Revenue, Customers, App usage
    unit: str       # count, money, percent
    source: str     # orders, customers, app_sessions


KPIS: list[KpiDef] = [
    KpiDef("Total Sales", "Sales", "count", "orders"),
    KpiDef("Average Order Value", "Sales", "money", "orders"),
    KpiDef("Total Revenue", "Revenue", "money", "orders"),
    KpiDef("Revenue Growth", "Revenue", "percent", "orders"),
    KpiDef("New Customers", "Customers", "count", "customers"),
    KpiDef("Customer Retention Rate", "Customers", "percent", "orders"),
    KpiDef("Active Users", "App usage", "count", "app_sessions"),
    KpiDef("Conversion Rate", "App usage", "percent", "app_sessions"),
]
KPI_BY_NAME = {k.name: k for k in KPIS}
KPI_NAMES = [k.name for k in KPIS]

FILTER_COLUMNS = [
    "region", "city", "product_category", "product_name",
    "sales_channel", "device", "payment_method",
]
FILTER_LABELS = {
    "region": "Region", "city": "City", "product_category": "Product category",
    "product_name": "Product name", "sales_channel": "Sales channel",
    "device": "Device", "payment_method": "Payment method",
}
# Cột nào lọc được cho nguồn nào. app_sessions lọc region/city qua khách hàng (user_id = customer_id).
FILTER_SUPPORT = {
    "orders": set(FILTER_COLUMNS),
    "customers": {"region", "city"},
    "app_sessions": {"region", "city"},
}

# ------------------------------------------------------------------ kỳ

PERIOD_LABELS = {
    "today": "Today",
    "last_7_days": "Last 7 days",
    "last_30_days": "Last 30 days",
    "this_month": "This month",
}


@dataclass(frozen=True)
class Period:
    start: date
    end: date                      # tính cả ngày end
    key: str = "custom"

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1

    @property
    def label(self) -> str:
        return PERIOD_LABELS.get(self.key, "Custom range")

    @property
    def dates_text(self) -> str:
        return format_range(self.start, self.end)

    def previous(self) -> "Period":
        """Kỳ liền trước, cùng độ dài, không trùng."""
        end = self.start - timedelta(days=1)
        return Period(end - timedelta(days=self.days - 1), end)

    def to_dict(self) -> dict:
        return {"key": self.key, "label": self.label, "start": self.start.isoformat(),
                "end": self.end.isoformat(), "days": self.days, "dates_text": self.dates_text}


def format_range(start: date, end: date) -> str:
    """'1 to 7 Nov', '25 Oct to 7 Nov', '8 Nov' (năm chỉ ghi khi khác năm hôm nay)."""
    def fmt(d: date, with_month: bool = True) -> str:
        s = str(d.day) + (d.strftime(" %b") if with_month else "")
        return s + (f" {d.year}" if with_month and d.year != config.TODAY.year else "")
    if start == end:
        return fmt(start)
    same_month = (start.year, start.month) == (end.year, end.month)
    return f"{fmt(start, with_month=not same_month)} to {fmt(end)}"


def resolve_period(key: str, today: date = config.TODAY) -> Period:
    if key == "today":
        return Period(today, today, key)
    if key == "last_7_days":
        return Period(today - timedelta(days=7), today - timedelta(days=1), key)
    if key == "last_30_days":
        return Period(today - timedelta(days=30), today - timedelta(days=1), key)
    if key == "this_month":
        return Period(today.replace(day=1), today, key)
    raise ValueError(f"Unknown period '{key}'")


def custom_period(start: date, end: date, today: date = config.TODAY) -> Period:
    if end < start:
        raise ValueError("The end date is before the start date.")
    if end > today:
        raise ValueError("The period cannot include dates in the future.")
    return Period(start, end)


# ------------------------------------------------------------------ bộ lọc

@dataclass(frozen=True)
class Filter:
    column: str
    value: str

    @property
    def label(self) -> str:
        return f"{FILTER_LABELS[self.column]}: {self.value}"


def parse_filter(text: Optional[str]) -> Optional[Filter]:
    """'region:North' -> Filter('region', 'North'). Rỗng -> None."""
    if not text:
        return None
    column, sep, value = text.partition(":")
    column, value = column.strip(), value.strip()
    if not sep or column not in FILTER_COLUMNS or not value:
        raise ValueError(f"Invalid filter '{text}'. Use <category>:<value>, "
                         f"category one of {', '.join(FILTER_COLUMNS)}.")
    return Filter(column, value)


# ------------------------------------------------------------------ kết quả

@dataclass
class KpiResult:
    name: str
    value: Optional[float]
    status: str = "ok"             # ok, no_data, not_applicable
    message: Optional[str] = None
    group: str = ""
    unit: str = ""
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def no_data_message(period: Period, flt: Optional[Filter]) -> str:
    msg = f"No data for {period.dates_text}"
    if flt:
        msg += f" with filter {flt.label}"
    return msg + "."


# ------------------------------------------------------------------ truy vấn

def _range_args(period: Period) -> tuple[str, str]:
    return period.start.isoformat() + " 00:00:00", (period.end + timedelta(days=1)).isoformat() + " 00:00:00"


def _orders_where(period: Period, flt: Optional[Filter]) -> tuple[str, list]:
    sql = "status = 'completed' AND order_datetime >= ? AND order_datetime < ?"
    args = list(_range_args(period))
    if flt:
        sql += f" AND {flt.column} = ?"   # column đã được kiểm tra trong FILTER_COLUMNS
        args.append(flt.value)
    return sql, args


def order_totals(conn: sqlite3.Connection, period: Period, flt: Optional[Filter] = None) -> tuple[int, float]:
    where, args = _orders_where(period, flt)
    count, revenue = conn.execute(
        f"SELECT COUNT(*), COALESCE(SUM(order_value), 0) FROM orders WHERE {where}", args
    ).fetchone()
    return count, round(revenue, 2)


def _buyers(conn: sqlite3.Connection, period: Period, flt: Optional[Filter]) -> set[str]:
    where, args = _orders_where(period, flt)
    return {r[0] for r in conn.execute(f"SELECT DISTINCT customer_id FROM orders WHERE {where}", args)}


def _new_customers(conn: sqlite3.Connection, period: Period, flt: Optional[Filter]) -> int:
    sql = "SELECT COUNT(*) FROM customers WHERE signup_date >= ? AND signup_date <= ?"
    args = [period.start.isoformat(), period.end.isoformat()]
    if flt:
        sql += f" AND {flt.column} = ?"
        args.append(flt.value)
    return conn.execute(sql, args).fetchone()[0]


def _app_users(conn: sqlite3.Connection, period: Period, flt: Optional[Filter]) -> tuple[int, int]:
    """(Active Users, số user có session converted = 1)."""
    sql = ("SELECT COUNT(DISTINCT user_id), COUNT(DISTINCT CASE WHEN converted = 1 THEN user_id END)"
           " FROM app_sessions WHERE session_datetime >= ? AND session_datetime < ?")
    args = list(_range_args(period))
    if flt:
        sql += f" AND user_id IN (SELECT customer_id FROM customers WHERE {flt.column} = ?)"
        args.append(flt.value)
    active, converted = conn.execute(sql, args).fetchone()
    return active, converted


# ------------------------------------------------------------------ API chính

def compute(conn: sqlite3.Connection, name: str, period: Period,
            flt: Optional[Filter] = None, compare_to: Optional[Period] = None) -> KpiResult:
    """Tính một KPI cho một kỳ và (tùy chọn) một bộ lọc.

    compare_to chỉ dùng cho Revenue Growth; mặc định là kỳ liền trước cùng độ dài.
    """
    kdef = KPI_BY_NAME.get(name)
    if kdef is None:
        raise ValueError(f"Unknown KPI '{name}'")
    res = KpiResult(name=name, value=None, group=kdef.group, unit=kdef.unit)

    if flt and flt.column not in FILTER_SUPPORT[kdef.source]:
        res.status = "not_applicable"
        res.message = f"The filter {flt.label} does not apply to {name}."
        return res

    def no_data(msg: Optional[str] = None) -> KpiResult:
        res.status = "no_data"
        res.message = msg or no_data_message(period, flt)
        return res

    if name in ("Total Sales", "Total Revenue", "Average Order Value"):
        count, revenue = order_totals(conn, period, flt)
        if count == 0:
            return no_data()
        res.value = {"Total Sales": count, "Total Revenue": revenue,
                     "Average Order Value": round(revenue / count, 2)}[name]

    elif name == "Revenue Growth":
        other = compare_to or period.previous()
        if other.days != period.days:
            raise ValueError("Revenue Growth needs two periods of the same length.")
        cur_count, cur_rev = order_totals(conn, period, flt)
        prev_count, prev_rev = order_totals(conn, other, flt)
        res.details = {"compare_start": other.start.isoformat(), "compare_end": other.end.isoformat(),
                       "revenue": cur_rev if cur_count else None,
                       "compare_revenue": prev_rev if prev_count else None}
        if cur_count == 0:
            return no_data()
        if prev_count == 0 or prev_rev == 0:
            return no_data(no_data_message(other, flt).replace("No data for", "No revenue to compare for"))
        res.value = (cur_rev - prev_rev) / prev_rev

    elif name == "New Customers":
        count = _new_customers(conn, period, flt)
        if count == 0:
            return no_data()
        res.value = count

    elif name == "Customer Retention Rate":
        prev = period.previous()
        current = _buyers(conn, period, flt)
        previous = _buyers(conn, prev, flt)
        res.details = {"compare_start": prev.start.isoformat(), "compare_end": prev.end.isoformat()}
        if not current:
            return no_data()
        if not previous:
            return no_data(no_data_message(prev, flt).replace("No data for", "No customers to compare for"))
        res.value = len(previous & current) / len(previous)

    elif name in ("Active Users", "Conversion Rate"):
        active, converted = _app_users(conn, period, flt)
        if active == 0:
            return no_data()
        res.value = active if name == "Active Users" else converted / active

    return res


def compute_all(conn: sqlite3.Connection, period: Period, flt: Optional[Filter] = None,
                names: Optional[list[str]] = None) -> list[KpiResult]:
    return [compute(conn, n, period, flt) for n in (names or KPI_NAMES)]
