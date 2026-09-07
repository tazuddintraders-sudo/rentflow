/* RentFlow — small shared helpers (vanilla JS, no dependencies) */
window.RF = window.RF || {};

RF.csrfToken = function () {
  const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return m ? m[0].split("=")[1] : (document.querySelector("[name=csrfmiddlewaretoken]") || {}).value || "";
};

RF.api = async function (url, options = {}) {
  const opts = Object.assign({ method: "GET", headers: {} }, options);
  opts.headers["X-CSRFToken"] = RF.csrfToken();
  if (opts.body && !(opts.body instanceof FormData) && typeof opts.body !== "string") {
    opts.body = JSON.stringify(opts.body);
    opts.headers["Content-Type"] = "application/json";
  }
  const resp = await fetch(url, opts);
  let data = {};
  try { data = await resp.json(); } catch (e) { /* no json */ }
  if (!resp.ok) {
    const err = new Error(data.errors ? data.errors.join(" ") : (data.error || `Request failed (${resp.status})`));
    err.data = data;
    throw err;
  }
  return data;
};

RF.money = function (n) {
  return "৳ " + Number(n || 0).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
};

RF.initial = function (name) {
  return (name || "?").trim().split(/\s+/).map(w => w[0]).slice(0, 2).join("").toUpperCase();
};

RF.debounce = function (fn, ms) {
  let t;
  return function (...args) { clearTimeout(t); t = setTimeout(() => fn.apply(this, args), ms); };
};

RF.qs = function (sel, root = document) { return root.querySelector(sel); };
RF.qsa = function (sel, root = document) { return Array.from(root.querySelectorAll(sel)); };
