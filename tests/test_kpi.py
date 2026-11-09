"""Đối chiếu module KPI với data/README.md và mục 7 của kế hoạch."""
import csv
from datetime import date

import pytest

from app import config, kpi

P = kpi.Period
NOV_1_7 = P(date(2026, 11, 1), date(2026, 11, 7))
SEP_15_21 = P(date(2026, 9, 15), date(2026, 9, 21))


def values(conn, period, flt=None):
    return {r.name: r for r in kpi.compute_all(conn, period, flt)}


def test_today_is_fixed_and_last_7_days_is_1_to_7_nov():
    assert config.TODAY == date(2026, 11, 8)
    p = kpi.resolve_period("last_7_days")
    assert (p.start, p.end) == (NOV_1_7.start, NOV_1_7.end)
    assert p.dates_text == "1 to 7 Nov"


def test_period_list():
    assert kpi.resolve_period("today").dates_text == "8 Nov"
    assert kpi.resolve_period("last_30_days").dates_text == "9 Oct to 7 Nov"
    assert kpi.resolve_period("this_month").dates_text == "1 to 8 Nov"


def test_dashboard_last_7_days(conn):
    v = values(conn, NOV_1_7)
    assert v["Total Sales"].value == 421
    assert v["Average Order Value"].value == 37.15
    assert v["Total Revenue"].value == 15641.04
    assert v["New Customers"].value == 112
    assert round(v["Customer Retention Rate"].value * 100, 1) == 8.2
    assert v["Customer Retention Rate"].details["compare_start"] == "2026-10-25"
    assert v["Active Users"].value == 1240
    assert round(v["Conversion Rate"].value * 100, 1) == 29.4
    assert all(r.status == "ok" for r in v.values())


def test_kpi_names_are_exact():
    assert kpi.KPI_NAMES == [
        "Total Sales", "Average Order Value", "Total Revenue", "Revenue Growth",
        "New Customers", "Customer Retention Rate", "Active Users", "Conversion Rate",
    ]


def test_period_comparison_1_7_nov_vs_15_21_sep(conn):
    a, b = values(conn, NOV_1_7), values(conn, SEP_15_21)
    assert b["Total Revenue"].value == 21116.56
    assert round(a["Total Revenue"].value - b["Total Revenue"].value, 2) == -5475.52
    assert (a["Total Sales"].value, b["Total Sales"].value) == (421, 589)
    assert (a["Active Users"].value, b["Active Users"].value) == (1240, 1237)
    growth = kpi.compute(conn, "Revenue Growth", NOV_1_7, compare_to=SEP_15_21)
    assert round(growth.value * 100, 1) == -25.9


def test_revenue_growth_needs_same_length(conn):
    with pytest.raises(ValueError):
        kpi.compute(conn, "Revenue Growth", NOV_1_7, compare_to=P(date(2026, 9, 1), date(2026, 9, 30)))


def test_filter_region_north(conn):
    v = values(conn, NOV_1_7, kpi.Filter("region", "North"))
    assert v["Total Sales"].value == 147
    assert v["Total Revenue"].value == 4929.98
    assert v["Active Users"].value == 384


def test_filter_not_applicable_is_reported(conn):
    r = kpi.compute(conn, "Active Users", NOV_1_7, kpi.Filter("product_name", "Moka Pot"))
    assert r.value is None and r.status == "not_applicable"
    assert "does not apply" in r.message
    r = kpi.compute(conn, "New Customers", NOV_1_7, kpi.Filter("sales_channel", "Website"))
    assert r.status == "not_applicable"


def test_no_app_usage_20_22_sep(conn):
    v = values(conn, P(date(2026, 9, 20), date(2026, 9, 22)))
    for name in ("Active Users", "Conversion Rate"):
        assert v[name].value is None and v[name].status == "no_data"
        assert "20 to 22 Sep" in v[name].message
    assert v["Total Sales"].value == 253
    assert v["Total Revenue"].value == 9078.17


def test_empty_filter_central_9_13_oct(conn):
    v = values(conn, P(date(2026, 10, 9), date(2026, 10, 13)), kpi.Filter("region", "Central"))
    assert v["Total Sales"].status == "no_data"
    assert v["Total Revenue"].value is None
    assert "Region: Central" in v["Total Revenue"].message
    assert v["New Customers"].value == 26


def test_period_before_data_has_no_data(conn):
    may = P(date(2026, 5, 20), date(2026, 5, 26))
    assert kpi.compute(conn, "Total Revenue", may).status == "no_data"
    growth = kpi.compute(conn, "Revenue Growth", NOV_1_7, compare_to=may)
    assert growth.value is None and "20 to 26 May" in growth.message


def test_refunded_orders_excluded_20_24_oct(conn):
    p = P(date(2026, 10, 20), date(2026, 10, 24))
    rows = conn.execute(
        "SELECT status, COUNT(*), SUM(order_value) FROM orders"
        " WHERE order_datetime >= '2026-10-20' AND order_datetime < '2026-10-25' GROUP BY status"
    ).fetchall()
    by_status = {r[0]: (r[1], r[2]) for r in rows}
    assert by_status["refunded"][0] > 0
    assert kpi.compute(conn, "Total Sales", p).value == by_status["completed"][0]
    assert kpi.compute(conn, "Total Revenue", p).value == round(by_status["completed"][1], 2)


def test_order_status_totals(conn):
    rows = dict(conn.execute("SELECT status, COUNT(*) FROM orders GROUP BY status").fetchall())
    assert rows == {"completed": 12097, "cancelled": 490, "refunded": 289}


def test_daily_answer_key(conn):
    """So từng ngày trong 160 ngày với kpi_daily_answer_key.csv (chỉ dùng trong test)."""
    with open(config.DATA_DIR / "kpi_daily_answer_key.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 160
    for row in rows:
        d = date.fromisoformat(row["date"])
        v = values(conn, P(d, d))
        assert v["Total Sales"].value == int(row["Total Sales"]), d
        assert v["Total Revenue"].value == pytest.approx(float(row["Total Revenue"]), abs=0.005), d
        assert v["Average Order Value"].value == pytest.approx(float(row["Average Order Value"]), abs=0.005), d
        assert (v["New Customers"].value or 0) == int(row["New Customers"]), d
        if row["Active Users"]:
            assert v["Active Users"].value == int(float(row["Active Users"])), d
            assert v["Conversion Rate"].value == pytest.approx(float(row["Conversion Rate"])), d
        else:
            assert v["Active Users"].status == "no_data", d


def test_parse_filter():
    assert kpi.parse_filter("region:North") == kpi.Filter("region", "North")
    assert kpi.parse_filter(None) is None
    for bad in ("North", "colour:red", "region:"):
        with pytest.raises(ValueError):
            kpi.parse_filter(bad)
