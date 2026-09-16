window.addEventListener("DOMContentLoaded", async () => {
  const breadcrumb = document.getElementById("breadcrumb");
  const list = document.getElementById("tariffs-list");

  // Get ?site_id from URL
  const params = new URLSearchParams(window.location.search);
  const siteId = params.get("site_id");

  try {
    // Fetch tariffs (filtered or all)
    const tariffs = siteId
      ? await API.req(`tariffs/?site_id=${encodeURIComponent(siteId)}`)
      : await API.req("tariffs/");

    // If filtered, try to derive site info for breadcrumb
    let siteName = null;
    if (siteId && tariffs.length > 0 && tariffs[0].site) {
      siteName = tariffs[0].site.name;
    }

    // Render breadcrumb dynamically
    const crumbs = [
      { label: "Home", href: "/site/" },
      { label: "Tariffs", href: "/site/pages/tariffs.html" },
    ];
    if (siteId && siteName) {
      crumbs.splice(1, 0, { label: "Sites", href: "/site/pages/sites.html" });
      crumbs.splice(2, 0, { label: siteName, href: `/site/pages/tariffs.html?site_id=${encodeURIComponent(siteId)}` });
    }
    renderBreadcrumb(breadcrumb, crumbs);

    // Render tariff list
    list.innerHTML = "";
    if (tariffs.length === 0) {
      list.innerHTML = "<li>No tariffs available.</li>";
    } else {
      tariffs.forEach((t) => {
        const li = document.createElement("li");
        li.className = "tariff-row";
        li.innerHTML = `
          <div class="tariff-name">${API.escapeHTML(t.name)}</div>
          <div class="tariff-meta">
            <span class="price">${t.price_per_kwh.toFixed(3)} €/kWh</span>
            <span class="site">(${API.escapeHTML(t.site?.name || "Unknown site")})</span>
          </div>
        `;
        list.appendChild(li);
      });
    }
  } catch (e) {
    console.error(e);
    list.innerHTML = "<li class='error'>Failed to load tariffs.</li>";
  }
});
