// site/assets/js/components/breadcrumb.js
// Renders a simple breadcrumb trail: [{label, href}, ...]
window.renderBreadcrumb = function (container, trail) {
  if (!container) return;
  container.innerHTML = trail
    .map((t, i) =>
      i < trail.length - 1
        ? `<a href="${t.href}">${t.label}</a> &rsaquo; `
        : `<span>${t.label}</span>`
    )
    .join("");
};
