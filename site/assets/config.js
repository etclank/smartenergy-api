// site/assets/config.js
// Default API base for local dev; can be changed at runtime & persisted.
window.SITE_API_BASE = localStorage.getItem("API_BASE") || "http://127.0.0.1:8000";

// Force mock with ?mock=1 or by flipping this to true.
window.SITE_USE_MOCK = false;
