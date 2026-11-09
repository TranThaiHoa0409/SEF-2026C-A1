"""Bước 3: trend, so sánh hai kỳ, bộ lọc, drill-down, no-data."""
from conftest import HOA, login


def trend(client, kpi="Total Revenue", period="last_7_days", flt=None):
    params = {"kpi": kpi, "period": period}
    if flt:
        params["filter"] = flt
    return client.get("/api/analytics/trend", params=params)


def compare(client, length=7, a="2026-11-01", b="2026-09-15", flt=None):
    params = {"length": length, "a_start": a, "b_start": b}
    if flt:
        params["filter"] = flt
    return client.get("/api/analytics/compare", params=params)


def rows(result):
    return {k["kpi"]: k for k in result["kpis"]}


# ------------------------------------------------------------------ trend

def test_trend_granularity_by_period(client):
    login(client, HOA)
    expected = {"today": ("hour", 24), "last_7_days": ("day", 7), "last_30_days": ("day", 30),
                "this_month": ("day", 8), "last_3_months": ("week", 13)}
    for period, (gran, n) in expected.items():
        t = trend(client, period=period).json()
        assert (t["granularity"], len(t["points"])) == (gran, n), period
    t = trend(client, period="last_3_months").json()
    assert t["period"]["dates_text"] == "9 Aug to 7 Nov"


def test_trend_offers_six_kpis(client):
    login(client, HOA)
    t = trend(client).json()
    assert t["kpis"] == ["Total Sales", "Average Order Value", "Total Revenue", "New Customers",
                         "Active Users", "Conversion Rate"]
    assert trend(client, kpi="Revenue Growth").status_code == 400
    assert trend(client, kpi="Customer Retention Rate").status_code == 400
    assert trend(client, period="last_year").status_code == 400


def test_trend_values_match_kpi_module(client):
    login(client, HOA)
    t = trend(client).json()
    assert t["total"] == 15641.04
    assert [p["value"] for p in t["points"]][2:5] == [662.5, 515.63, 2985.05]
    weeks = trend(client, kpi="Total Sales", period="last_3_months").json()
    assert weeks["points"][-1]["label"] == "1 to 7 Nov" and weeks["points"][-1]["value"] == 421


def test_trend_with_filter(client):
    login(client, HOA)
    t = trend(client, kpi="Total Sales", flt="region:North").json()
    assert t["filter"]["label"] == "Region: North"
    assert sum(p["value"] for p in t["points"]) == 147 and t["total"] == 147
    users = trend(client, kpi="Active Users", flt="region:North").json()
    assert users["total"] == 384


def test_trend_filter_not_applicable(client):
    login(client, HOA)
    t = trend(client, kpi="Active Users", flt="product_name:Moka Pot").json()
    assert t["status"] == "not_applicable" and "does not apply" in t["message"]


def test_trend_no_data_messages(client):
    login(client, HOA)
    t = trend(client, period="today").json()
    assert t["status"] == "no_data" and "8 Nov" in t["message"]


# ------------------------------------------------------------------ bộ lọc

def test_filter_values_come_from_data(client):
    login(client, HOA)
    cats = {c["column"]: c for c in client.get("/api/analytics/filters").json()["categories"]}
    assert list(cats) == ["region", "city", "product_category", "product_name",
                          "sales_channel", "device", "payment_method"]
    assert cats["region"]["values"] == ["Central", "North", "South"]
    assert "Cold Brew Kit" in cats["product_name"]["values"]
    assert "Active Users" in cats["region"]["applies_to"]
    assert "Active Users" not in cats["product_name"]["applies_to"]


def test_marketplace_outage_14_15_sep(client):
    login(client, HOA)
    r = client.get("/api/kpis", params={"start": "2026-09-14", "end": "2026-09-15",
                                        "filter": "sales_channel:Marketplace"}).json()
    v = {k["name"]: k for k in r["kpis"]}
    assert v["Total Sales"]["status"] == "no_data" and "Sales channel: Marketplace" in v["Total Sales"]["message"]


def test_cold_brew_kit_only_from_october(client):
    login(client, HOA)
    before = client.get("/api/kpis", params={"start": "2026-06-01", "end": "2026-09-30",
                                             "filter": "product_name:Cold Brew Kit"}).json()
    assert {k["name"]: k for k in before["kpis"]}["Total Sales"]["status"] == "no_data"


# ------------------------------------------------------------------ so sánh

def test_compare_1_7_nov_vs_15_21_sep(client):
    login(client, HOA)
    r = compare(client).json()
    assert (r["a"]["dates_text"], r["b"]["dates_text"]) == ("1 to 7 Nov", "15 to 21 Sep")
    k = rows(r)
    rev = k["Total Revenue"]
    assert (rev["a"], rev["b"], rev["difference"]) == (15641.04, 21116.56, -5475.52)
    assert round(rev["percent"] * 100, 1) == -25.9
    assert round(k["Revenue Growth"]["value"] * 100, 1) == -25.9
    sales = k["Total Sales"]
    assert (sales["a"], sales["b"], sales["difference"]) == (421, 589, -168)
    assert round(sales["percent"] * 100, 1) == -28.5
    users = k["Active Users"]
    assert (users["a"], users["b"], users["difference"]) == (1240, 1237, 3)
    assert round(users["percent"] * 100, 1) == 0.2
    assert r["notices"] == []


def test_compare_fills_same_length(client):
    login(client, HOA)
    r = compare(client, length=30, a="2026-10-09", b="2026-08-01").json()
    assert (r["a"]["end"], r["b"]["end"]) == ("2026-11-07", "2026-08-30")
    assert r["a"]["days"] == r["b"]["days"] == 30


def test_compare_rejects_overlap_same_dates_future_and_bad_length(client):
    login(client, HOA)
    overlap = compare(client, a="2026-11-01", b="2026-10-28")
    assert overlap.status_code == 400 and "overlap" in overlap.json()["detail"]
    assert compare(client, a="2026-11-01", b="2026-11-01").status_code == 400
    future = compare(client, a="2026-11-05", b="2026-09-15")
    assert future.status_code == 400 and "future" in future.json()["detail"]
    assert compare(client, length=14).status_code == 400


def test_compare_with_period_before_data(client):
    login(client, HOA)
    r = compare(client, b="2026-05-20").json()
    # Trước 1 Jun không có đơn hay phiên app, nhưng vẫn có khách đăng ký (New Customers).
    assert r["a_has_data"] and r["b_has_data"]
    assert len(r["notices"]) == 1
    note = r["notices"][0]
    assert "Period B (20 to 26 May) has no data for Total Sales" in note and "Only the other period" in note
    assert "New Customers" not in note and rows(r)["New Customers"]["b_status"] == "ok"
    k = rows(r)["Total Revenue"]
    assert k["a"] == 15641.04 and k["b"] is None and k["difference"] is None


def test_compare_with_filter(client):
    login(client, HOA)
    r = compare(client, flt="region:North").json()
    k = rows(r)
    assert k["Total Sales"]["a"] == 147 and k["Active Users"]["a"] == 384
    assert r["filter"]["label"] == "Region: North"


def test_compare_central_9_13_oct_no_orders(client):
    login(client, HOA)
    r = compare(client, length=1, a="2026-10-10", b="2026-09-10", flt="region:Central").json()
    assert rows(r)["Total Sales"]["a_status"] == "no_data"


# ------------------------------------------------------------------ drill-down

def drill(client, kpi="Total Revenue", start="2026-11-03 00:00:00", end="2026-11-04 00:00:00", flt=None):
    params = {"kpi": kpi, "start": start, "end": end}
    if flt:
        params["filter"] = flt
    return client.get("/api/analytics/drilldown", params=params)


def test_drilldown_3_nov(client):
    login(client, HOA)
    d = drill(client).json()
    assert len(d["rows"]) == 16
    done = [r for r in d["rows"] if r["status"] == "completed"]
    assert len(done) == 15 and round(sum(r["order_value"] for r in done), 2) == 662.5
    assert d["value"] == 662.5
    assert "status" in d["columns"]


def test_drilldown_matches_chart_point(client):
    login(client, HOA)
    t = trend(client, kpi="Total Sales", flt="region:North").json()
    p = t["points"][0]
    d = drill(client, kpi="Total Sales", start=p["start"], end=p["end"], flt="region:North").json()
    assert d["value"] == p["value"]
    assert all(r["region"] == "North" for r in d["rows"])
    assert sum(r["status"] == "completed" for r in d["rows"]) == p["value"]


def test_drilldown_refunds_listed_but_not_counted_20_24_oct(client):
    login(client, HOA)
    d = drill(client, start="2026-10-20 00:00:00", end="2026-10-25 00:00:00").json()
    refunded = [r for r in d["rows"] if r["status"] == "refunded"]
    assert refunded
    assert d["value"] == round(sum(r["order_value"] for r in d["rows"] if r["status"] == "completed"), 2)


def test_drilldown_other_sources(client):
    login(client, HOA)
    nc = drill(client, kpi="New Customers").json()
    assert nc["value"] == len(nc["rows"]) == 17
    au = drill(client, kpi="Active Users").json()
    assert au["value"] == len({r["user_id"] for r in au["rows"]}) == 55


def test_drilldown_empty_point(client):
    login(client, HOA)
    d = drill(client, start="2026-09-20 00:00:00", end="2026-09-21 00:00:00", kpi="Active Users").json()
    assert d["status"] == "no_data" and d["rows"] == [] and "20 Sep" in d["message"]
    d = drill(client, start="2026-10-10 00:00:00", end="2026-10-11 00:00:00", flt="region:Central").json()
    assert d["status"] == "no_data" and "Region: Central" in d["message"]


def test_drilldown_bad_input(client):
    login(client, HOA)
    assert drill(client, kpi="Revenue Growth").status_code == 400
    assert drill(client, start="2026-11-04 00:00:00", end="2026-11-03 00:00:00").status_code == 400
    assert drill(client, start="3 Nov").status_code == 400
