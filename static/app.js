// Trang tạm của bước 1: đăng nhập mẫu, 8 KPI kỳ Last 7 days, upload cho Admin.
const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const res = await fetch(path, options);
  const body = await res.json().catch(() => ({}));
  if (res.status === 401) { showSignin(); throw new Error(body.detail); }
  if (!res.ok) throw new Error(body.detail || res.statusText);
  return body;
}

function formatValue(k) {
  if (k.status !== "ok") return k.message;
  if (k.unit === "money") return "$" + k.value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  if (k.unit === "percent") return (k.value * 100).toFixed(1) + "%";
  return k.value.toLocaleString("en-US");
}

async function showSignin() {
  $("home").hidden = true; $("signin").hidden = false; $("who").textContent = "";
  const accounts = await fetch("/api/auth/accounts").then((r) => r.json());
  $("accounts").replaceChildren(...accounts.map((a) => {
    const b = document.createElement("button");
    b.textContent = `${a.name} · ${a.system_role}` + (a.is_active ? "" : " (deactivated)");
    b.disabled = !a.is_active;
    b.onclick = async () => {
      try {
        await api("/api/auth/login", { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_id: a.id }) });
        showHome();
      } catch (e) { $("signin-error").textContent = e.message; }
    };
    return b;
  }));
}

async function showHome() {
  const me = await api("/api/auth/me");
  $("signin").hidden = true; $("home").hidden = false; $("admin").hidden = !me.is_admin;
  const out = document.createElement("button");
  out.className = "secondary"; out.textContent = `${me.name} · Sign out`;
  out.onclick = async () => { await api("/api/auth/logout", { method: "POST" }); showSignin(); };
  $("who").replaceChildren(out);
  await loadKpis();
}

async function loadKpis() {
  const data = await api("/api/kpis?period=last_7_days");
  $("period-title").textContent = `${data.period.label}: ${data.period.dates_text}`;
  $("refresh").textContent = data.last_refresh ? `Data refreshed ${data.last_refresh.refreshed_at}` : "";
  $("kpis").replaceChildren(...data.kpis.map((k) => {
    const d = document.createElement("div");
    d.className = "card " + k.status;
    d.innerHTML = `<div class="name"></div><div class="value"></div>`;
    d.querySelector(".name").textContent = k.name;
    d.querySelector(".value").textContent = formatValue(k);
    return d;
  }));
}

$("upload-form").onsubmit = async (e) => {
  e.preventDefault();
  const pre = $("upload-result");
  pre.hidden = false;
  try {
    const r = await api("/api/uploads", { method: "POST", body: new FormData(e.target) });
    pre.textContent = JSON.stringify(r, null, 2);
    await loadKpis();
  } catch (err) { pre.textContent = err.message; }
};

showHome().catch(() => {});
