window.addEventListener("DOMContentLoaded", async () => {
  const breadcrumb = document.getElementById("breadcrumb");
  renderBreadcrumb(breadcrumb, [
    { label: "Home", href: "/site/" },
    { label: "Sites", href: "/site/pages/sites.html" }
  ]);

  const list = document.getElementById("sites-list");
  try {
    const sites = await API.req("sites/");
    list.innerHTML = "";
    sites.forEach((s) => {
      const li = document.createElement("li");
      li.innerHTML = `<a href="/site/pages/meters.html?site_id=${s.id}">${API.escapeHTML(s.name)}</a> – ${API.escapeHTML(s.location || "")}`;
      list.appendChild(li);
    });
  } catch (e) {
    console.error(e);
    list.innerHTML = "<li class='error'>Failed to load sites.</li>";
  }
});
