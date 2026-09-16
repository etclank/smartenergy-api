// site/assets/js/components/breadcrumb.js
// Renders a simple breadcrumb trail: [{label, href}, ...]
window.renderBreadcrumb = function (container, trail) {
  if (!container) return;
  container.innerHTML = trail
    .map((t, i) =>
      i < trail.length - 1
        ? `<a href="${API.escapeHTML(t.href)}">${API.escapeHTML(t.label)}</a> &rsaquo; `
        : `<span>${API.escapeHTML(t.label)}</span>`
    )
    .join("");
};
