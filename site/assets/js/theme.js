(() => {
  const btn = document.getElementById("theme-toggle");
  const root = document.documentElement;
  const current = localStorage.getItem("theme") || "dark";
  apply(current);

  btn?.addEventListener("click", () => {
    const next = root.dataset.theme === "dark" ? "light" : "dark";
    apply(next);
    localStorage.setItem("theme", next);
  });

  function apply(mode){
    root.dataset.theme = mode;
    if(mode==="light"){
      root.style.setProperty("--bg","#f5f7fa");
      root.style.setProperty("--card-bg","#ffffff");
      root.style.setProperty("--text","#222");
    } else {
      root.style.setProperty("--bg","#0f1320");
      root.style.setProperty("--card-bg","#1b2134");
      root.style.setProperty("--text","#e8ecf3");
    }
  }
})();
