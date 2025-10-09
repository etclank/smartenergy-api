// site/assets/js/charts.js
window.renderEnergyChart = (ctx, datasets) => {
  const isDark = document.documentElement.dataset.theme !== "light";
  const gridColor = isDark ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.1)";
  const textColor = isDark ? "#e8ecf3" : "#222";

  const adapter = Chart?._adapters?._date;

  // --- Determine time unit automatically ---
  const allX = datasets.flatMap(d => d.data.map(p => new Date(p.x).getTime()));
  const spanHours = allX.length > 1 ? (Math.max(...allX) - Math.min(...allX)) / 3_600_000 : 0;
  let unit = "hour";
  if (spanHours > 48) unit = "day";
  if (spanHours > 24 * 14) unit = "week";

  // --- Calculate Y min/max for better fit ---
  const allY = datasets.flatMap(d => d.data.map(p => p.y));
  const yMin = Math.min(...allY);
  const yMax = Math.max(...allY);
  const yPadding = (yMax - yMin) * 0.1;

  const chart = new Chart(ctx, {
    type: "line",
    data: { datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      animation: {
        duration: 600,
        easing: "easeOutQuart",
      },
      transitions: {
        resize: {
          animation: { duration: 0 },
        },
      },
      scales: {
        x: {
          type: "time",
          time: {
            unit,
            tooltipFormat: "yyyy-MM-dd HH:mm",
            displayFormats: {
              hour: "MMM d HH:mm",
              day: "MMM d",
              week: "MMM d",
            },
          },
          grid: { color: gridColor },
          ticks: {
            color: textColor,
            maxRotation: 45,
            autoSkip: true,
          },
          title: { display: true, text: "Date / Time (UTC)", color: textColor },
        },
        y: {
          min: yMin - yPadding,
          max: yMax + yPadding,
          grid: { color: gridColor },
          ticks: { color: textColor },
          title: { display: true, text: "kWh / kW", color: textColor },
        },
      },
      elements: {
        line: { tension: 0.3, borderWidth: 2 },
        point: { radius: 0 },
      },
      plugins: {
        legend: {
          position: "bottom",
          labels: { color: textColor, usePointStyle: true },
        },
        tooltip: {
          backgroundColor: isDark ? "#1b2134" : "#f0f0f0",
          titleColor: isDark ? "#fff" : "#000",
          bodyColor: isDark ? "#e8ecf3" : "#000",
          callbacks: {
            title: (items) => {
              const t = items[0]?.parsed?.x;
              return t ? new Date(t).toLocaleString() : "";
            },
            label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y.toFixed(2)}`,
          },
        },
      },
    },
  });

  return chart;
};

// --- Helper: Smooth theme transition ---
window.updateChartsTheme = (theme) => {
  if (!window.Chart || !Chart.instances) return;
  Object.values(Chart.instances).forEach((chart) => {
    if (!chart?.canvas) return;
    const canvas = chart.canvas;
    const datasets = chart.config.data.datasets;
    const newCtx = canvas.getContext("2d");
    chart.destroy();
    renderEnergyChart(newCtx, datasets);
  });
};
