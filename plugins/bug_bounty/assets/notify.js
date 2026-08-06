/* Private per-hunter toast notifications for bug report status changes.
 * Polls a per-user endpoint (server marks each seen on read => delivered once,
 * even across tabs) and renders a self-contained toast. No Bootstrap/global
 * dependencies so it works on any page and in both light/dark themes. */
(function () {
  if (window.__bugNotifyLoaded) return;
  window.__bugNotifyLoaded = true;

  var STATUS = {
    pending: { c: "#8b95a5", i: "fa-clock" },
    triaging: { c: "#17a2b8", i: "fa-magnifying-glass" },
    accepted: { c: "#28c76f", i: "fa-circle-check" },
    rejected: { c: "#ea5455", i: "fa-circle-xmark" },
    duplicate: { c: "#ffb703", i: "fa-clone" },
    informative: { c: "#8b95a5", i: "fa-circle-info" },
    not_applicable: { c: "#ea5455", i: "fa-ban" },
    spam: { c: "#b71c1c", i: "fa-triangle-exclamation" },
    comment: { c: "#5d94ff", i: "fa-comment-dots" },
  };

  function root() {
    return (window.init && window.init.urlRoot) || "";
  }

  function ensureStyles() {
    if (document.getElementById("bug-notify-style")) return;
    var css = [
      "#bug-notify-wrap{position:fixed;top:76px;right:20px;z-index:20000;display:flex;flex-direction:column;gap:12px;max-width:380px;pointer-events:none}",
      ".bug-notify{pointer-events:auto;display:flex;align-items:flex-start;gap:12px;background:#12151c;color:#e7ecf3;border:1px solid rgba(255,255,255,.08);border-left:4px solid #28c76f;border-radius:12px;padding:14px 14px 14px 13px;box-shadow:0 12px 40px rgba(0,0,0,.45);font-family:'Inter',system-ui,sans-serif;transform:translateX(120%);opacity:0;transition:transform .35s cubic-bezier(.22,1,.36,1),opacity .35s}",
      ".bug-notify.show{transform:translateX(0);opacity:1}",
      ".bug-notify-ico{flex:0 0 auto;width:34px;height:34px;border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:15px;background:rgba(255,255,255,.06)}",
      ".bug-notify-body{flex:1 1 auto;min-width:0}",
      ".bug-notify-kicker{font-size:.62rem;letter-spacing:.14em;text-transform:uppercase;font-weight:700;color:#8b95a5;margin:0 0 3px;font-family:'JetBrains Mono',monospace}",
      ".bug-notify-msg{font-size:.9rem;line-height:1.35;font-weight:500;margin:0;word-wrap:break-word}",
      ".bug-notify-msg b{font-weight:700}",
      ".bug-notify-x{flex:0 0 auto;background:none;border:0;color:#6b7280;font-size:16px;line-height:1;cursor:pointer;padding:2px 4px;margin:-2px -2px 0 0}",
      ".bug-notify-x:hover{color:#e7ecf3}",
    ].join("");
    var s = document.createElement("style");
    s.id = "bug-notify-style";
    s.textContent = css;
    document.head.appendChild(s);
  }

  function wrap() {
    var w = document.getElementById("bug-notify-wrap");
    if (!w) {
      w = document.createElement("div");
      w.id = "bug-notify-wrap";
      document.body.appendChild(w);
    }
    return w;
  }

  function esc(s) {
    return (s == null ? "" : String(s)).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  // Bold the "..." quoted program name and the trailing status word.
  function decorate(msg) {
    var out = esc(msg);
    out = out.replace(/&quot;(.*?)&quot;/g, "&quot;<b>$1</b>&quot;");
    return out;
  }

  function toast(n) {
    ensureStyles();
    var meta = STATUS[n.status] || STATUS.pending;
    var el = document.createElement("div");
    el.className = "bug-notify";
    el.style.borderLeftColor = meta.c;
    el.innerHTML =
      '<div class="bug-notify-ico" style="color:' + meta.c + '"><i class="fas ' + meta.i + '"></i></div>' +
      '<div class="bug-notify-body">' +
      '<p class="bug-notify-kicker">' + esc(n.title || "Report update") + "</p>" +
      '<p class="bug-notify-msg">' + decorate(n.message) + "</p>" +
      "</div>" +
      '<button class="bug-notify-x" aria-label="Dismiss">&times;</button>';
    wrap().appendChild(el);

    var dismiss = function () {
      el.classList.remove("show");
      setTimeout(function () { if (el.parentNode) el.parentNode.removeChild(el); }, 400);
    };
    el.querySelector(".bug-notify-x").addEventListener("click", dismiss);
    requestAnimationFrame(function () {
      requestAnimationFrame(function () { el.classList.add("show"); });
    });
    setTimeout(dismiss, 8000);
  }

  function lastKey() {
    return "bugLastToast_" + ((window.init && window.init.userId) || "0");
  }
  function getLastToast() {
    try { return parseInt(localStorage.getItem(lastKey()), 10) || 0; }
    catch (e) { return 0; }
  }
  function setLastToast(id) {
    try { localStorage.setItem(lastKey(), String(id)); } catch (e) {}
  }
  // Alpine loads as a deferred module, so it may not exist when our first poll
  // returns — and the theme's own init sets unread_count from core
  // notifications (0) after us. Remember the value and re-apply until it
  // sticks.
  var lastUnread = null;
  function applyBadge() {
    if (lastUnread === null) return;
    try {
      if (window.Alpine && typeof window.Alpine.store === "function") {
        window.Alpine.store("unread_count", lastUnread);
      }
    } catch (e) {}
  }
  function setBadge(n) {
    lastUnread = n || 0;
    applyBadge();
  }
  document.addEventListener("alpine:init", function () {
    setTimeout(applyBadge, 0);
  });
  setTimeout(applyBadge, 1500);
  setTimeout(applyBadge, 4000);

  var polling = false;
  function poll() {
    if (polling) return;
    polling = true;
    fetch(root() + "/bug/notifications", {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    })
      .then(function (r) { return r.ok ? r.json() : { data: [], unread: 0 }; })
      .then(function (resp) {
        var list = (resp && resp.data) ? resp.data : [];
        setBadge(resp && resp.unread);

        var known = localStorage.getItem(lastKey()) !== null;
        var maxId = list.reduce(function (m, n) { return n.id > m ? n.id : m; }, 0);
        var last = getLastToast();

        // First time on this browser: remember where we are, don't blast the
        // backlog as toasts (the notifications center still lists them).
        if (!known) { setLastToast(maxId); return; }

        // Toast only genuinely-new items, oldest first.
        var fresh = list.filter(function (n) { return n.id > last; })
          .sort(function (a, b) { return a.id - b.id; });
        fresh.forEach(function (n, i) {
          setTimeout(function () { toast(n); }, i * 350);
        });
        if (maxId > last) setLastToast(maxId);
      })
      .catch(function () {})
      .then(function () { polling = false; });
  }

  function start() {
    poll();
    setInterval(poll, 30000);
    document.addEventListener("visibilitychange", function () {
      if (!document.hidden) poll();
    });
    window.addEventListener("focus", poll);
  }

  // Only for logged-in users
  if (window.init && window.init.userId) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", start);
    } else {
      start();
    }
  }
})();
