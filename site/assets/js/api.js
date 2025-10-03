// site/assets/js/api.js
(() => {
  const params = new URLSearchParams(window.location.search);
  const FORCE_MOCK = params.get("mock") === "1" || window.SITE_USE_MOCK === true;

  const norm = (s) => (s || "").trim().replace(/\/+$/, "");

  function getBase() {
    const saved = localStorage.getItem("API_BASE");
    return norm(saved || window.SITE_API_BASE || "");
  }
  function setBase(v) {
    const n = norm(v);
    localStorage.setItem("API_BASE", n);
    window.SITE_API_BASE = n;
    return n;
  }

  function getToken() {
    return localStorage.getItem("API_TOKEN") || "";
  }
  function setToken(t) {
    if (t) localStorage.setItem("API_TOKEN", t);
    else localStorage.removeItem("API_TOKEN");
  }

  async function req(path, opts = {}) {
    const base = getBase();
    const url = `${base}/${path}`.replace(/([^:]\/)\/+/g, "$1");
    const headers = Object.assign({ "content-type": "application/json" }, opts.headers || {});
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
    const res = await fetch(url, { ...opts, headers, credentials: "omit", cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const ct = res.headers.get("content-type") || "";
    return ct.includes("application/json") ? res.json() : res.text();
  }

  // API calls
  const api = {
    getBase, setBase, getToken, setToken, forceMock: FORCE_MOCK,

    healthz: () => req("healthz"),
    cachez:  () => req("cachez"),

    // Auth (optional)
    login:   (username, password) => req("auth/login", { method: "POST", body: JSON.stringify({ username, password }) }),
    me:      () => req("auth/me"),

    // Data
    async metersList() {
      if (!FORCE_MOCK) {
        try { return await req("meters/"); } 
        catch (e) { console.warn("metersList live failed, falling back to mock:", e); }
      }
      const r = await fetch("site/mock/meters.json", { cache: "no-store" });
      if (!r.ok) throw new Error(`mock HTTP ${r.status}`);
      return r.json();
    },
    async meterById(id) {
      if (!FORCE_MOCK) {
        try { return await req(`meters/${encodeURIComponent(id)}`); }
        catch (e) { console.warn("meterById live failed, no mock detail available:", e); throw e; }
      }
      // If needed, synthesize from list:
      const all = await api.metersList();
      return all.find((m) => String(m.id) === String(id)) || null;
    },
  };

  // Page auto-initializers (run only if matching elements exist)
  async function initLanding() {
    const healthEl = document.getElementById("health");
    const cacheEl  = document.getElementById("cache");
    const baseIn   = document.getElementById("apiBase");
    const saveBtn  = document.getElementById("saveApiBase");
    const docs     = document.getElementById("openDocs");
    const redoc    = document.getElementById("openRedoc");
    const whoAmI   = document.getElementById("whoAmI");
    if (!healthEl || !baseIn) return;

    baseIn.value = api.getBase();
    const updateDocLinks = () => {
      const b = api.getBase();
      docs.href = `${b}/docs`; redoc.href = `${b}/redoc`;
    };
    updateDocLinks();

    const setBadge = (el, txt, cls) => { el.textContent = txt; el.className = `badge ${cls}`; };

    try { await api.healthz(); setBadge(healthEl, "API: up", "badge-live"); }
    catch { setBadge(healthEl, "API: down", "badge-error"); }

    try { const c = await api.cachez(); c?.redis === "up" ? setBadge(cacheEl, "Redis: up", "badge-live") : setBadge(cacheEl, "Redis: down", "badge-mock"); }
    catch { setBadge(cacheEl, "Redis: error", "badge-error"); }

    saveBtn.addEventListener("click", () => {
      api.setBase(baseIn.value);
      baseIn.value = api.getBase();
      updateDocLinks();
      window.location.reload();
    });

    // Optional: show whoami if we have a token
    const t = api.getToken();
    if (t && whoAmI) {
      try { const me = await api.me(); whoAmI.textContent = `Signed in as ${me?.username ?? me?.sub ?? "unknown"}`; }
      catch { whoAmI.textContent = "Auth token invalid."; }
    }
  }

  async function initMetersList() {
    const list = document.getElementById("meters-list");
    const banner = document.getElementById("demo-banner");
    if (!list || !banner) return;

    try {
      const meters = await api.metersList();
      list.innerHTML = "";
      if (Array.isArray(meters) && meters.length) {
        meters.forEach((m) => {
          const li = document.createElement("li");
          li.className = "meter-row";
          const link = document.createElement("a");
          link.href = `/pages/meter.html?id=${encodeURIComponent(m.id)}`;
          link.textContent = `${m.name} — ${m.location || ""}`;
          li.appendChild(link);
          list.appendChild(li);
        });
      } else {
        list.innerHTML = '<li class="empty">No meters found.</li>';
      }
      banner.textContent = api.forceMock ? "Demo (mock data)" : "Demo (live data)";
      banner.className = api.forceMock ? "badge badge-mock" : "badge badge-live";
    } catch (err) {
      console.error(err);
      list.innerHTML = '<li class="error">Failed to load data. Try adding ?mock=1</li>';
      banner.textContent = "Demo (error)";
      banner.className = "badge badge-error";
    }
  }

  async function initMeterDetail() {
    const details = document.getElementById("meter-detail");
    if (!details) return;
    const id = new URLSearchParams(window.location.search).get("id");
    if (!id) { details.textContent = "Missing meter id"; return; }
    try {
      const m = await api.meterById(id);
      if (!m) { details.textContent = "Meter not found"; return; }
      details.innerHTML = `
        <div class="card">
          <div class="k">ID</div><div class="v">${m.id}</div>
          <div class="k">Name</div><div class="v">${m.name}</div>
          <div class="k">Location</div><div class="v">${m.location || ""}</div>
        </div>`;
    } catch (e) {
      console.error(e);
      details.textContent = "Failed to load meter.";
    }
  }

  window.API = api; // expose for other scripts/pages

  window.addEventListener("DOMContentLoaded", () => {
    initLanding();
    initMetersList();
    initMeterDetail();
  });
})();
