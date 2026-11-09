// BizBoard prototype: đăng nhập mẫu, dashboard, danh mục widget, snapshot, upload (Admin).
const $ = (id) => document.getElementById(id);
const PERIODS = [["today", "Today"], ["last_7_days", "Last 7 days"], ["last_30_days", "Last 30 days"], ["this_month", "This month"]];
let me = null;
let charts = [];

// ------------------------------------------------------------------ tiện ích

async function api(path, options = {}) {
  if (options.json !== undefined) {
    options = { ...options, headers: { "Content-Type": "application/json" }, body: JSON.stringify(options.json) };
  }
  const res = await fetch(path, options);
  const body = await res.json().catch(() => ({}));
  if (res.status === 401) { me = null; show("signin"); throw new Error(body.detail || "Please sign in."); }
  if (!res.ok) { const e = new Error(body.detail || res.statusText); e.status = res.status; throw e; }
  return body;
}

function el(tag, attrs = {}, ...children) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") n.className = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else n.setAttribute(k, v);
  }
  n.append(...children.filter((c) => c !== null && c !== undefined));
  return n;
}

function fmt(value, unit) {
  if (value === null || value === undefined) return "–";
  if (unit === "money") return "$" + value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  if (unit === "percent") return (value * 100).toFixed(1) + "%";
  return value.toLocaleString("en-US");
}

function toast(text) {
  const t = $("toast");
  t.textContent = text; t.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => (t.hidden = true), 2500);
}

function show(view) {
  document.querySelectorAll(".view").forEach((v) => (v.hidden = v.id !== "view-" + view));
  $("nav").hidden = view === "signin";
  document.querySelectorAll("nav a").forEach((a) => a.classList.toggle("active", a.getAttribute("href") === "#/" + view));
}

function showError(e) {
  if (e.status === 403 || e.status === 404) { $("error-text").textContent = e.message; show("error"); }
  else toast(e.message);
}

// ------------------------------------------------------------------ đăng nhập

async function renderSignin() {
  $("who").replaceChildren();
  const accounts = await fetch("/api/auth/accounts").then((r) => r.json());
  $("accounts").replaceChildren(...accounts.map((a) => el("button", {
    ...(a.is_active ? {} : { disabled: "" }),
    onclick: async () => {
      try {
        await api("/api/auth/login", { method: "POST", json: { user_id: a.id } });
        await loadMe(); location.hash = "#/dashboard"; route();
      } catch (e) { $("signin-error").textContent = e.message; }
    },
  }, `${a.name} · ${a.system_role}` + (a.is_active ? "" : " (deactivated)"))));
  show("signin");
}

async function loadMe() {
  me = await api("/api/auth/me");
  $("nav-upload").hidden = !me.is_admin;
  $("who").replaceChildren(el("button", {
    class: "secondary",
    onclick: async () => { await api("/api/auth/logout", { method: "POST" }); me = null; renderSignin(); },
  }, `${me.name} · Sign out`));
}

// ------------------------------------------------------------------ widget

function renderWidget(w) {
  const card = el("div", { class: `card ${w.type} ${w.status}`, "data-id": w.id },
    el("div", { class: "name" }, w.name));
  if (w.status !== "ok") {
    card.append(el("div", { class: "nodata" }, w.message));
  } else if (w.type === "summary") {
    let text = fmt(w.value, w.unit);
    if (w.kpi === "Revenue Growth" && w.value > 0) text = "+" + text;
    card.append(el("div", { class: "value" }, text));
    if (w.details && w.details.compare_start) {
      card.append(el("div", { class: "sub" }, `Compared with ${w.details.compare_start} to ${w.details.compare_end}`));
    }
  } else {
    const canvas = el("canvas", { "aria-label": `${w.kpi} trend chart`, role: "img" });
    card.append(canvas);
    charts.push(new Chart(canvas, {
      type: "line",
      data: {
        labels: w.points.map((p) => p.label),
        datasets: [{ data: w.points.map((p) => p.value), borderColor: "#1f6f4a", backgroundColor: "#1f6f4a",
          tension: 0, pointRadius: w.points.length > 24 ? 0 : 3, spanGaps: false }],
      },
      options: {
        responsive: true, maintainAspectRatio: false, animation: false,
        plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => fmt(c.parsed.y, w.unit) } } },
        scales: { y: { beginAtZero: true, ticks: { callback: (v) => (w.unit === "money" ? "$" + v.toLocaleString("en-US") : fmt(v, w.unit)) } },
                  x: { ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 7 } } },
      },
    }));
  }
  return card;
}

function clearCharts() { charts.forEach((c) => c.destroy()); charts = []; }

// ------------------------------------------------------------------ dashboard

let sortable = null;

async function renderDashboard() {
  show("dashboard");
  const d = await api("/api/dashboard");
  $("periods").replaceChildren(...PERIODS.map(([key, label]) => el("button", {
    "aria-pressed": String(d.period.key === key),
    onclick: async () => { await api("/api/dashboard/period", { method: "PUT", json: { period_key: key } }); renderDashboard(); },
  }, label)));
  $("period-title").textContent = `${d.period.label}: ${d.period.dates_text}`;
  $("refresh").textContent = d.last_refresh ? `Data refreshed ${d.last_refresh.refreshed_at}` : "";
  $("skipped").replaceChildren(...d.skipped.map((s) => el("p", { class: "notice" }, s)));
  clearCharts();
  $("widgets").replaceChildren(...d.widgets.map((w) => renderWidget(w)));
  if (sortable) sortable.destroy();
  sortable = Sortable.create($("widgets"), {
    animation: 150, delay: 300, delayOnTouchOnly: true,   // điện thoại: nhấn giữ rồi kéo
    onEnd: async (ev) => {
      if (ev.oldIndex === ev.newIndex) return;
      const ids = [...$("widgets").children].map((c) => c.dataset.id);
      try { await api("/api/dashboard/layout", { method: "PUT", json: { widget_ids: ids } }); toast("Layout saved"); }
      catch (e) { toast(e.message); renderDashboard(); }
    },
  });
}

$("reset-layout").onclick = async () => {
  await api("/api/dashboard/layout/reset", { method: "POST" });
  toast("Layout reset to the default order"); renderDashboard();
};

$("capture").onclick = async () => {
  try {
    const s = await api("/api/snapshots", { method: "POST", json: {} });
    toast(`Snapshot "${s.name}" saved`);
  } catch (e) { toast(e.message); }
};

// ------------------------------------------------------------------ danh mục widget

let catalogue = null;
let selected = new Set();   // lựa chọn đang sửa, chỉ lưu khi bấm Save

async function openCatalogue() {
  catalogue = await api("/api/widgets");
  selected = new Set(catalogue.widgets.filter((w) => w.added).map((w) => w.id));
  $("catalogue-period").textContent = `No-data marks are for ${catalogue.period.label}: ${catalogue.period.dates_text}.`;
  $("catalogue-search").value = "";
  $("catalogue-error").textContent = "";
  renderCatalogue();
  $("catalogue").showModal();
}

function renderCatalogue() {
  const q = $("catalogue-search").value.trim().toLowerCase();
  const blocks = [];
  for (const g of catalogue.groups) {
    const items = catalogue.widgets.filter((w) => w.group === g && w.name.toLowerCase().includes(q));
    if (!items.length) continue;
    blocks.push(el("h3", {}, g));
    for (const w of items) {
      const input = el("input", { type: "checkbox", value: w.id, ...(selected.has(w.id) ? { checked: "" } : {}),
        onchange: (e) => (e.target.checked ? selected.add(w.id) : selected.delete(w.id)) });
      blocks.push(el("label", { class: "option" }, input, el("span", {}, w.name),
        w.no_data ? el("span", { class: "tag" }, "No data") : null));
    }
  }
  if (!blocks.length) blocks.push(el("p", { class: "muted" }, "No widget matches your search."));
  $("catalogue-list").replaceChildren(...blocks);
}

$("open-catalogue").onclick = () => openCatalogue().catch(showError);
$("catalogue-search").oninput = renderCatalogue;
$("catalogue-cancel").onclick = () => $("catalogue").close();   // đóng không lưu: giữ lựa chọn cũ
$("catalogue-default").onclick = async () => {
  await api("/api/dashboard/reset", { method: "POST" });
  $("catalogue").close(); toast("Dashboard reset to the default widgets"); renderDashboard();
};
$("catalogue-form").onsubmit = async (e) => {
  e.preventDefault();
  // Giữ thứ tự danh mục; server giữ vị trí cũ và thêm widget mới vào cuối.
  const ids = catalogue.widgets.map((w) => w.id).filter((id) => selected.has(id));
  try {
    await api("/api/dashboard/selection", { method: "PUT", json: { widget_ids: ids } });
    $("catalogue").close(); toast("Widgets saved"); renderDashboard();
  } catch (err) { $("catalogue-error").textContent = err.message; }
};

// ------------------------------------------------------------------ snapshot

function snapItem(s, canDelete) {
  const period = s.period ? `${s.period.label}: ${s.period.dates_text}` : `${s.period_start} to ${s.period_end}`;
  const owner = canDelete ? "" : ` · from ${s.owner_name}`;
  return el("li", {},
    el("a", { href: `#/snapshot/${s.id}` }, el("strong", {}, s.name),
      el("span", { class: "muted" }, `${period} · captured ${s.captured_at}${owner}`)),
    canDelete ? el("button", { class: "danger", onclick: async () => {
      if (!confirm(`Delete "${s.name}"? Everyone it was shared with loses access.`)) return;
      await api(`/api/snapshots/${s.id}`, { method: "DELETE" }); renderSnapshots();
    } }, "Delete") : null);
}

async function renderSnapshots() {
  show("snapshots");
  const d = await api("/api/snapshots");
  const empty = (t) => el("li", {}, el("span", { class: "muted" }, t));
  $("snap-mine").replaceChildren(...(d.mine.length ? d.mine.map((s) => snapItem(s, true))
    : [empty("No snapshots yet. Use Capture snapshot on the dashboard.")]));
  $("snap-shared").replaceChildren(...(d.shared_with_me.length ? d.shared_with_me.map((s) => snapItem(s, false))
    : [empty("Nothing has been shared with you.")]));
}

async function renderSnapshot(id) {
  const s = await api(`/api/snapshots/${id}`);
  show("snapshot");
  $("snap-name").textContent = s.name;
  const owner = s.can_delete ? "" : ` · shared by ${s.owner_name || s.owner_id}`;
  $("snap-meta").textContent = `${s.data.period.label}: ${s.data.period.dates_text} · captured ${s.captured_at}${owner}`;
  clearCharts();
  $("snap-widgets").replaceChildren(...s.data.widgets.map((w) => renderWidget(w)));
}

// ------------------------------------------------------------------ analytics

const an = {
  tab: "trend", kpi: "Total Revenue", period: "last_7_days", filter: null,   // filter: {column, value, label}
  categories: null, chart: null, compared: false,
};

function filterParam() { return an.filter ? `&filter=${encodeURIComponent(an.filter.column + ":" + an.filter.value)}` : ""; }

async function renderAnalytics() {
  show("analytics");
  if (!an.categories) {
    an.categories = (await api("/api/analytics/filters")).categories;
    $("filter-column").append(...an.categories.map((c) => el("option", { value: c.column }, c.label)));
  }
  setTab(an.tab);
}

function setTab(tab) {
  an.tab = tab;
  $("tab-trend").setAttribute("aria-pressed", String(tab === "trend"));
  $("tab-compare").setAttribute("aria-pressed", String(tab === "compare"));
  $("panel-trend").hidden = tab !== "trend";
  $("panel-compare").hidden = tab !== "compare";
  renderFilterChip();
  if (tab === "trend") loadTrend().catch(showError);
  else { updateCompareEnds(); if (an.compared) runCompare(); }
}
$("tab-trend").onclick = () => setTab("trend");
$("tab-compare").onclick = () => setTab("compare");

// Bộ lọc: chọn danh mục rồi chọn giá trị; một bộ lọc một lúc.
$("filter-column").onchange = () => {
  const cat = an.categories.find((c) => c.column === $("filter-column").value);
  $("filter-value-wrap").hidden = !cat;
  if (!cat) { setFilter(null); return; }
  $("filter-value").replaceChildren(el("option", { value: "" }, "Choose a value"),
    ...cat.values.map((v) => el("option", { value: v }, v)));
};
$("filter-value").onchange = () => {
  const cat = an.categories.find((c) => c.column === $("filter-column").value);
  const v = $("filter-value").value;
  if (cat && v) setFilter({ column: cat.column, value: v, label: `${cat.label}: ${v}` });
};
function setFilter(f) {
  an.filter = f;
  if (!f) { $("filter-column").value = ""; $("filter-value-wrap").hidden = true; }
  setTab(an.tab);
}
function renderFilterChip() {
  $("filter-chip").hidden = !an.filter;
  $("filter-chip-text").textContent = an.filter ? `Filter: ${an.filter.label}` : "";
}
$("filter-clear").onclick = () => setFilter(null);

// Trend
async function loadTrend() {
  const t = await api(`/api/analytics/trend?kpi=${encodeURIComponent(an.kpi)}&period=${an.period}${filterParam()}`);
  if (!$("trend-kpi").options.length) {
    $("trend-kpi").append(...t.kpis.map((k) => el("option", { value: k }, k)));
  }
  $("trend-kpi").value = an.kpi;
  $("trend-periods").replaceChildren(...t.periods.map((p) => el("button", {
    "aria-pressed": String(p.key === an.period), onclick: () => { an.period = p.key; loadTrend().catch(showError); },
  }, p.label)));
  const byWhat = { hour: "by hour", day: "by day", week: "by week" }[t.granularity];
  $("trend-title").textContent = `${t.name} · ${t.period.label}: ${t.period.dates_text}`;
  $("trend-sub").textContent = t.status === "ok"
    ? `Shown ${byWhat}. Whole period: ${fmt(t.total, t.unit)}` + (an.filter ? ` · ${an.filter.label}` : "") : "";
  const empty = t.status !== "ok";
  $("trend-nodata").hidden = !empty;
  $("trend-chart-box").hidden = empty;
  $("nodata-clear").hidden = !an.filter;
  if (empty) {
    $("trend-nodata-text").textContent = t.status === "no_data"
      ? `${t.message} Choose another period${an.filter ? " or clear the filter" : ""}.` : t.message;
    return;
  }
  if (an.chart) an.chart.destroy();
  an.chart = new Chart($("trend-chart"), {
    type: "line",
    data: { labels: t.points.map((p) => p.label),
      datasets: [{ data: t.points.map((p) => p.value), borderColor: "#1f6f4a", backgroundColor: "#1f6f4a",
        tension: 0, pointRadius: 4, pointHoverRadius: 7, pointHitRadius: 14 }] },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      interaction: { mode: "nearest", intersect: false },
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => fmt(c.parsed.y, t.unit) } } },
      scales: { y: { beginAtZero: true, ticks: { callback: (v) => (t.unit === "money" ? "$" + v.toLocaleString("en-US") : fmt(v, t.unit)) } },
                x: { ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 7 } } },
      onClick: (evt, items) => { if (items.length) openDrill(t.points[items[0].index]).catch(showError); },
    },
  });
}
$("trend-kpi").onchange = () => { an.kpi = $("trend-kpi").value; loadTrend().catch(showError); };
$("nodata-period").onclick = () => $("trend-periods").querySelector("button").focus();
$("nodata-clear").onclick = () => setFilter(null);

// Drill-down
const RECORD_VIEWS = {
  orders: (r) => [r.order_id, r.status, `${r.order_datetime} · ${r.product_name} × ${r.quantity}`,
    `${r.region}, ${r.city} · ${r.sales_channel} · ${r.payment_method}`, fmt(r.order_value, "money"), r.status !== "completed"],
  customers: (r) => [r.customer_id, r.segment, `${r.full_name} · signed up ${r.signup_date}`,
    `${r.region}, ${r.city} · ${r.acquisition_source}`, "", false],
  app_sessions: (r) => [r.session_id, r.converted ? "converted" : "no purchase", `${r.session_datetime} · ${r.platform}`,
    `User ${r.user_id} · ${r.pages_viewed} pages · ${Math.round(r.duration_seconds / 60)} min`, "", false],
};

async function openDrill(point) {
  const d = await api(`/api/analytics/drilldown?kpi=${encodeURIComponent(an.kpi)}`
    + `&start=${encodeURIComponent(point.start)}&end=${encodeURIComponent(point.end)}${filterParam()}`);
  $("drill-title").textContent = `${d.kpi} · ${point.label}`;
  $("drill-meta").textContent = `${point.start.slice(0, 16)} to ${point.end.slice(0, 16)}`
    + (an.filter ? ` · Filter: ${an.filter.label}` : " · No filter");
  const kind = d.columns.includes("order_id") ? "orders" : d.columns.includes("session_id") ? "app_sessions" : "customers";
  if (d.status !== "ok") {
    $("drill-summary").textContent = d.message;
    $("drill-list").replaceChildren();
  } else {
    let summary = `${d.rows.length} records · ${d.kpi}: ${fmt(d.value, d.unit)}`;
    if (kind === "orders") {
      const done = d.rows.filter((r) => r.status === "completed").length;
      summary += ` (from ${done} completed orders; cancelled and refunded orders are listed but not counted)`;
    }
    $("drill-summary").textContent = summary;
    $("drill-list").replaceChildren(...d.rows.map((r) => {
      const [id, tag, line1, line2, amount, excluded] = RECORD_VIEWS[kind](r);
      return el("div", { class: "record" + (excluded ? " excluded" : "") },
        el("div", { class: "top" }, el("span", {}, id, " ", el("span", { class: "badge" }, tag)), el("span", {}, amount)),
        el("div", {}, line1), el("div", { class: "muted" }, line2));
    }));
  }
  $("drill").showModal();
}
$("drill-back").onclick = () => $("drill").close();   // biểu đồ giữ nguyên

// Compare
function addDays(iso, n) { const d = new Date(iso + "T00:00:00Z"); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); }
function updateCompareEnds() {
  const len = Number($("cmp-length").value);
  for (const k of ["a", "b"]) {
    const v = $(`cmp-${k}`).value;
    $(`cmp-${k}-end`).textContent = v ? `Ends ${addDays(v, len - 1)} (${len} day${len > 1 ? "s" : ""})` : "";
  }
}
["cmp-length", "cmp-a", "cmp-b"].forEach((id) => ($(id).oninput = updateCompareEnds));
$("compare-form").onsubmit = (e) => { e.preventDefault(); an.compared = true; runCompare(); };

async function runCompare() {
  $("cmp-error").textContent = "";
  let r;
  try {
    r = await api(`/api/analytics/compare?length=${$("cmp-length").value}&a_start=${$("cmp-a").value}&b_start=${$("cmp-b").value}${filterParam()}`);
  } catch (e) {
    $("cmp-error").textContent = e.message; $("cmp-result").replaceChildren(); $("cmp-notices").replaceChildren(); return;
  }
  let notices = r.notices;
  if (!r.a_has_data && !r.b_has_data) {
    notices = [`No data for either period${an.filter ? " with filter " + an.filter.label : ""}. Change the dates or clear the filter.`];
  }
  $("cmp-notices").replaceChildren(...notices.map((n) => el("p", { class: "notice" }, n)));
  const A = `A · ${r.a.dates_text}`, B = `B · ${r.b.dates_text}`;
  $("cmp-result").replaceChildren(...r.kpis.map((k) => {
    const card = el("div", { class: "card" }, el("div", { class: "name" }, k.kpi));
    if (k.is_growth) {
      card.append(k.status === "ok"
        ? el("div", { class: "value " + (k.value >= 0 ? "up" : "down") }, (k.value > 0 ? "+" : "") + fmt(k.value, "percent"))
        : el("div", { class: "nodata" }, k.message));
      card.append(el("div", { class: "sub" }, `Total Revenue of ${A} compared with ${B}`));
      return card;
    }
    const cell = (v, st, msg) => (st === "ok" ? el("div", { class: "num" }, fmt(v, k.unit)) : el("div", { class: "nodata" }, msg));
    card.append(el("div", { class: "cmp-row" },
      el("div", { class: "label" }, A), el("div", { class: "label" }, B),
      cell(k.a, k.a_status, k.a_message), cell(k.b, k.b_status, k.b_message)));
    if (k.difference !== null) {
      const sign = k.difference > 0 ? "+" : k.difference < 0 ? "−" : "";
      const absDiff = k.unit === "percent" ? `${(Math.abs(k.difference) * 100).toFixed(1)} pts` : fmt(Math.abs(k.difference), k.unit);
      const pct = k.percent === null ? "" : ` (${k.percent > 0 ? "+" : k.percent < 0 ? "−" : ""}${Math.abs(k.percent * 100).toFixed(1)}%)`;
      card.append(el("div", { class: "cmp-diff " + (k.difference >= 0 ? "up" : "down") }, `Difference: ${sign}${absDiff}${pct}`));
    }
    return card;
  }));
}

// ------------------------------------------------------------------ upload

$("upload-form").onsubmit = async (e) => {
  e.preventDefault();
  const pre = $("upload-result");
  pre.hidden = false;
  try {
    const r = await api("/api/uploads", { method: "POST", body: new FormData(e.target) });
    pre.textContent = JSON.stringify(r, null, 2);
  } catch (err) { pre.textContent = err.message; }
};

// ------------------------------------------------------------------ điều hướng

async function route() {
  if (!me) { try { await loadMe(); } catch { return renderSignin(); } }
  const [, page, id] = (location.hash || "#/dashboard").split("/");
  try {
    if (page === "analytics") await renderAnalytics();
    else if (page === "snapshots") await renderSnapshots();
    else if (page === "snapshot") await renderSnapshot(id);
    else if (page === "upload" && me.is_admin) show("upload");
    else if (page === "upload") { $("error-text").textContent = "No access: you do not have permission to view or change this item."; show("error"); }
    else await renderDashboard();
  } catch (e) { showError(e); }
}

window.addEventListener("hashchange", route);
route();
