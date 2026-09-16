// site/assets/js/api.js
(() => {
  const params = new URLSearchParams(window.location.search);
  const FORCE_MOCK = params.get("mock") === "1" || window.SITE_USE_MOCK === true;

  const norm = (s) => (s || "").trim().replace(/\/+$/, "");

  function getBase() {
    const saved = localStorage.getItem("API_BASE");
    return norm(saved || window.SITE_API_BASE || "/api");
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
    const headers = { "content-type": "application/json", ...(opts.headers || {}) };
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
    const res = await fetch(url, { ...opts, headers, credentials: "omit", cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const ct = res.headers.get("content-type") || "";
    return ct.includes("application/json") ? res.json() : res.text();
  }

  const escapeHTML = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  const api = {
    escapeHTML,
    getBase, setBase, getToken, setToken, req, forceMock: FORCE_MOCK,

    healthz: () => req("health/z"),
    cachez:  () => req("health/cachez"),

    login: (username, password) =>
      req("auth/login", { method: "POST", body: JSON.stringify({ username, password }) }),
    me: () => req("auth/me"),

    async metersList() {
      if (!FORCE_MOCK) {
        try { return await req("meters/"); }
        catch (e) { console.warn("metersList live failed, using mock:", e); }
      }
      const r = await fetch("/site/mock/meters.json", { cache: "no-store" });
      if (!r.ok) throw new Error(`mock HTTP ${r.status}`);
      return r.json();
    },
    async meterById(id) {
      if (!FORCE_MOCK) {
        try { return await req(`meters/${encodeURIComponent(id)}`); }
        catch (e) { console.warn("meterById live failed:", e); throw e; }
      }
      const all = await api.metersList();
      return all.find((m) => String(m.id) === String(id)) || null;
    },

    // --- Energy data ---
    async energyImported(meter_id) { return await req(`energy_imported/?meter_id=${meter_id}`); },
    async energyExported(meter_id) { return await req(`energy_exported/?meter_id=${meter_id}`); },
    async energyReactive(meter_id) { return await req(`energy_reactive/?meter_id=${meter_id}`); },
    async maxPower(meter_id)      { return await req(`max_power/?meter_id=${meter_id}`); },

    // --- Tariffs ---
    async tariffsList() { return await req("tariffs/"); },
  };

  // Landing page status checks
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
      const b = api.getBase().replace(/\/api$/, "");
      if (docs) docs.href = `${b}/docs`;
      if (redoc) redoc.href = `${b}/redoc`;
    };
    updateDocLinks();

    const setBadge = (el, txt, cls) => {
      if (el) { el.textContent = txt; el.className = `badge ${cls}`; }
    };

    try { await api.healthz(); setBadge(healthEl, "API: up", "badge-live"); }
    catch { setBadge(healthEl, "API: down", "badge-error"); }

    try {
      const c = await api.cachez();
      c?.redis === "up"
        ? setBadge(cacheEl, "Redis: up", "badge-live")
        : setBadge(cacheEl, "Redis: down", "badge-mock");
    } catch { setBadge(cacheEl, "Redis: error", "badge-error"); }

    saveBtn?.addEventListener("click", () => {
      api.setBase(baseIn.value);
      baseIn.value = api.getBase();
      updateDocLinks();
      window.location.reload();
    });

    const t = api.getToken();
    if (t && whoAmI) {
      try {
        const me = await api.me();
        whoAmI.textContent = `Signed in as ${me?.username ?? me?.sub ?? "unknown"}`;
      } catch { whoAmI.textContent = "Auth token invalid."; }
    }
  }

  // Expose API globally
  window.API = api;

  // --- Theme handling ---
  function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("THEME", theme);
  }

  function toggleTheme() {
    const current = localStorage.getItem("THEME") || "dark";
    const next = current === "dark" ? "light" : "dark";
    applyTheme(next);
    updateChartsTheme(next);
  }

  function initTheme() {
    const saved = localStorage.getItem("THEME") || "dark";
    applyTheme(saved);
    const btn = document.getElementById("theme-toggle");
    if (btn) {
      btn.textContent = saved === "dark" ? "🌙" : "☀️";
      btn.addEventListener("click", () => {
        toggleTheme();
        btn.textContent =
          document.documentElement.dataset.theme === "dark" ? "🌙" : "☀️";
      });
    }
  }

  // Notify charts when theme changes
  function updateChartsTheme(theme) {
    if (window.Chart && Chart.instances) {
      Object.values(Chart.instances).forEach((chart) => {
        const canvas = chart.canvas;
        const datasets = chart.config.data.datasets;
        chart.destroy();
        renderEnergyChart(canvas, datasets);
      });
    }
  }

  // Initialize all on load
  window.addEventListener("DOMContentLoaded", () => {
    initTheme();
    initLanding();
  });
})();
