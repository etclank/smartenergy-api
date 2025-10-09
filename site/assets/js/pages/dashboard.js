// site/assets/js/pages/dashboard.js
window.addEventListener("DOMContentLoaded", async () => {
  // 1️⃣ Initialize health badges
  try {
    await Promise.all([API.healthz(), API.cachez()]);
    document.getElementById("health").textContent = "API: up";
    document.getElementById("health").className = "badge badge-live";
    document.getElementById("cache").textContent = "Redis: up";
    document.getElementById("cache").className = "badge badge-live";
  } catch {
    document.getElementById("health").textContent = "API error";
    document.getElementById("health").className = "badge badge-error";
  }

  // 2️⃣ Load data concurrently
  try {
    const [sites, meters] = await Promise.all([
      API.req("sites/"),
      API.req("meters/"),
    ]);

    // Aggregate energy and power
    const allMeterIds = meters.map((m) => m.id);
    let importedSum = 0, exportedSum = 0, maxPowerVals = [];

    for (const id of allMeterIds) {
      const [imp, exp, maxp] = await Promise.all([
        API.energyImported(id),
        API.energyExported(id),
        API.maxPower(id),
      ]);

      importedSum += imp.reduce((s, r) => s + (r.measure_value || 0), 0);
      exportedSum += exp.reduce((s, r) => s + (r.measure_value || 0), 0);
      maxPowerVals.push(...maxp.map((r) => r.measure_value || 0));
    }

    const avgMaxP =
      maxPowerVals.length > 0
        ? (maxPowerVals.reduce((a, b) => a + b, 0) / maxPowerVals.length).toFixed(2)
        : 0;

    // 3️⃣ Display
    document.getElementById("sum-imported").textContent = importedSum.toFixed(1);
    document.getElementById("sum-exported").textContent = exportedSum.toFixed(1);
    document.getElementById("avg-maxp").textContent = avgMaxP;
    document.getElementById("count-sites").textContent = `${sites.length} / ${meters.length}`;
  } catch (e) {
    console.error("[dashboard] Error loading summary:", e);
    document.querySelectorAll("#summary-cards .v").forEach((el) => (el.textContent = "ERR"));
  }
});
