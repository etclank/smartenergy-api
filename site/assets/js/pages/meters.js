window.addEventListener("DOMContentLoaded", async () => {
  const list = document.getElementById("meters-list");
  const params = new URLSearchParams(window.location.search);
  const siteId = params.get("site_id");

  // 🧭 Breadcrumb
  const trail = [
    { label: "Home", href: "/site/" },
    { label: "Sites", href: "/site/pages/sites.html" }
  ];
  if (siteId) trail.push({ label: `Site ${siteId}`, href: `/site/pages/meters.html?site_id=${siteId}` });
  trail.push({ label: "Meters", href: "/site/pages/meters.html" });
  renderBreadcrumb(document.getElementById("breadcrumb"), trail);

  try {
    const all = await API.req("meters/");
    const meters = siteId ? all.filter((m) => String(m.site_id) === siteId) : all;
    list.innerHTML = "";
    meters.forEach((m) => {
      const li = document.createElement("li");
      li.innerHTML = `<a href="/site/pages/meter.html?id=${m.id}">${m.name}</a> — ${m.location || ""}`;
      list.appendChild(li);
    });
  } catch (e) {
    console.error(e);
    list.innerHTML = "<li class='error'>Failed to load meters.</li>";
  }
});
