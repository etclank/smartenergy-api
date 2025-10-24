// site/assets/js/pages/system.js
window.addEventListener("DOMContentLoaded", async () => {
  // 🧭 Breadcrumb
  renderBreadcrumb(document.getElementById("breadcrumb"), [
    { label: "Home", href: "/site/" },
    { label: "System Health", href: "/site/pages/system.html" }
  ]);

  const cpuChart = new Chart(document.getElementById("cpuChart"), {
    type: "doughnut",
    data: { datasets: [{ data: [0, 100], backgroundColor: ["#36a2eb", "#2a3045"], borderWidth: 0 }] },
    options: { cutout: "80%", plugins: { legend: { display: false } } },
  });

  const memChart = new Chart(document.getElementById("memChart"), {
    type: "doughnut",
    data: { datasets: [{ data: [0, 100], backgroundColor: ["#ff6384", "#2a3045"], borderWidth: 0 }] },
    options: { cutout: "80%", plugins: { legend: { display: false } } },
  });

  const uptimeChart = new Chart(document.getElementById("uptimeChart"), {
    type: "line",
    data: { labels: [], datasets: [{ label: "Uptime (h)", data: [], borderColor: "#5cc8ff", fill: false }] },
    options: { scales: { y: { beginAtZero: true } }, plugins: { legend: { display: false } } },
  });

  const latencyDiv = document.getElementById("latencyStats");

  async function refresh() {
    try {
      // Use the unified API helper, just like other pages
      const data = await API.req("system_metrics/latest");
      const cpu = data.cpu_percent || 0;
      const mem = data.mem_percent || 0;
      const uph = (data.uptime_seconds || 0) / 3600;

      cpuChart.data.datasets[0].data = [cpu, 100 - cpu];
      memChart.data.datasets[0].data = [mem, 100 - mem];
      cpuChart.update();
      memChart.update();

      uptimeChart.data.labels.push(new Date().toLocaleTimeString());
      uptimeChart.data.datasets[0].data.push(uph);
      if (uptimeChart.data.labels.length > 20) {
        uptimeChart.data.labels.shift();
        uptimeChart.data.datasets[0].data.shift();
      }
      uptimeChart.update();

      latencyDiv.innerHTML = `
        <b>DB:</b> ${data.db_latency_ms} ms &nbsp;
        <b>Redis:</b> ${data.redis_latency_ms} ms &nbsp;
        <b>CPU:</b> ${cpu.toFixed(1)}% &nbsp;
        <b>Mem:</b> ${mem.toFixed(1)}% &nbsp;
        <b>Uptime:</b> ${uph.toFixed(1)} h
      `;
    } catch (err) {
      console.error("[system] refresh failed:", err);
      latencyDiv.textContent = "Error fetching system metrics.";
    }
  }

  await refresh();
  setInterval(refresh, 30000);
});
