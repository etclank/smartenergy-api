window.addEventListener("DOMContentLoaded", async () => {
  const id = new URLSearchParams(window.location.search).get("id");
  const detail = document.getElementById("meter-detail");
  const charts = document.getElementById("energy-charts");
  const startIn = document.getElementById("startDate");
  const endIn = document.getElementById("endDate");
  const applyBtn = document.getElementById("applyRange");
  const resetBtn = document.getElementById("resetRange");

  renderBreadcrumb(document.getElementById("breadcrumb"), [
    { label: "Home", href: "/site/" },
    { label: "Sites", href: "/site/pages/sites.html" },
    { label: "Meters", href: "/site/pages/meters.html" },
    { label: `Meter ${id}`, href: `/site/pages/meter.html?id=${id}` },
  ]);

  if (!id) return (detail.textContent = "Missing meter id");

  try {
    const m = await API.meterById(id);
    detail.innerHTML = `
      <div class="card">
        <div class="k">Name</div><div class="v">${API.escapeHTML(m.name)}</div>
        <div class="k">Location</div><div class="v">${API.escapeHTML(m.location)}</div>
        <div class="k">Serial</div><div class="v">${API.escapeHTML(m.serial_number)}</div>
        <div class="k">Type</div><div class="v">${API.escapeHTML(m.type)}</div>
      </div>`;

    // --- Fetch datasets ---
    const [imp, exp, reac, maxp] = await Promise.all([
      API.energyImported(id),
      API.energyExported(id),
      API.energyReactive(id),
      API.maxPower(id),
    ]);

    window.METER_DATA = { imp, exp, reac, maxp };

    // --- Initial render ---
    const ctx = document.createElement("canvas");
    charts.innerHTML = "";
    charts.appendChild(ctx);

    renderEnergyChart(ctx, [
      { label: "Imported kWh", data: window.METER_DATA.imp.map(r => ({ x: r.timestamp, y: r.measure_value })), borderColor: "#5cc8ff" },
      { label: "Exported kWh", data: window.METER_DATA.exp.map(r => ({ x: r.timestamp, y: r.measure_value })), borderColor: "#ff8c5c" },
      { label: "Reactive kvarh (imp)", data: window.METER_DATA.reac.map(r => ({ x: r.timestamp, y: r.imported_kvarh })), borderColor: "#a0ff5c" },
      { label: "Reactive kvarh (exp)", data: window.METER_DATA.reac.map(r => ({ x: r.timestamp, y: r.exported_kvarh })), borderColor: "#ff5cf0" },
      { label: "Max Power kW", data: window.METER_DATA.maxp.map(r => ({ x: r.timestamp, y: r.measure_value })), borderColor: "#ffe15c" },
    ]);

    // --- Date range controls ---
    applyBtn?.addEventListener("click", () => {
      const s = startIn.value ? new Date(startIn.value).getTime() : -Infinity;
      const e = endIn.value ? new Date(endIn.value).getTime() + 86400000 : Infinity;

      const filter = (arr) => arr.filter(r => {
        const t = new Date(r.timestamp).getTime();
        return t >= s && t <= e;
      });

      const ctx2 = document.createElement("canvas");
      charts.innerHTML = "";
      charts.appendChild(ctx2);

      renderEnergyChart(ctx2, [
        { label: "Imported kWh", data: filter(window.METER_DATA.imp).map(r => ({ x: r.timestamp, y: r.measure_value })), borderColor: "#5cc8ff" },
        { label: "Exported kWh", data: filter(window.METER_DATA.exp).map(r => ({ x: r.timestamp, y: r.measure_value })), borderColor: "#ff8c5c" },
        { label: "Reactive kvarh (imp)", data: filter(window.METER_DATA.reac).map(r => ({ x: r.timestamp, y: r.imported_kvarh })), borderColor: "#a0ff5c" },
        { label: "Reactive kvarh (exp)", data: filter(window.METER_DATA.reac).map(r => ({ x: r.timestamp, y: r.exported_kvarh })), borderColor: "#ff5cf0" },
        { label: "Max Power kW", data: filter(window.METER_DATA.maxp).map(r => ({ x: r.timestamp, y: r.measure_value })), borderColor: "#ffe15c" },
      ]);
    });

    resetBtn?.addEventListener("click", () => {
      startIn.value = "";
      endIn.value = "";
      const ctx3 = document.createElement("canvas");
      charts.innerHTML = "";
      charts.appendChild(ctx3);
      renderEnergyChart(ctx3, [
        { label: "Imported kWh", data: window.METER_DATA.imp.map(r => ({ x: r.timestamp, y: r.measure_value })), borderColor: "#5cc8ff" },
        { label: "Exported kWh", data: window.METER_DATA.exp.map(r => ({ x: r.timestamp, y: r.measure_value })), borderColor: "#ff8c5c" },
        { label: "Reactive kvarh (imp)", data: window.METER_DATA.reac.map(r => ({ x: r.timestamp, y: r.imported_kvarh })), borderColor: "#a0ff5c" },
        { label: "Reactive kvarh (exp)", data: window.METER_DATA.reac.map(r => ({ x: r.timestamp, y: r.exported_kvarh })), borderColor: "#ff5cf0" },
        { label: "Max Power kW", data: window.METER_DATA.maxp.map(r => ({ x: r.timestamp, y: r.measure_value })), borderColor: "#ffe15c" },
      ]);
    });
  } catch (e) {
    console.error("[meter] error loading data", e);
    charts.textContent = "Failed to load meter data.";
  }
});
