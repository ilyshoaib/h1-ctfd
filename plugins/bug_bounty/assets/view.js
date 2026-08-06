CTFd._internal.challenge.data = undefined;
CTFd._internal.challenge.renderer = null;
CTFd._internal.challenge.render = null;

CTFd._internal.challenge.preRender = function () {};

// The modal HTML is injected by Alpine *after* this script runs, so poll for
// our container, then load the hunter's report history.
CTFd._internal.challenge.postRender = function () {
  bugInitObserver();
  bugMaybeLoad(document);
};

CTFd._internal.challenge.submit = function () {
  return Promise.resolve({ data: { status: "incorrect", message: "Use the report form." } });
};

function bugUrlRoot() {
  return (window.init && window.init.urlRoot) || (CTFd.config && CTFd.config.urlRoot) || "";
}
function bugNonce() {
  return (window.init && window.init.csrfNonce) || (CTFd.config && CTFd.config.csrfNonce) || "";
}
function bugEsc(s) {
  return (s == null ? "" : String(s)).replace(/[&<>"']/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
  });
}
function bugWhenReady(sel, cb, tries) {
  var el = document.querySelector(sel);
  if (el) return cb(el);
  if (tries <= 0) return;
  setTimeout(function () { bugWhenReady(sel, cb, tries - 1); }, 50);
}
function bugFmtDate(iso) {
  if (!iso) return "";
  try { return new Date(iso).toLocaleString(); } catch (e) { return iso; }
}

var BUG_STATUS = {
  pending: "#6c757d", triaging: "#17a2b8", accepted: "#28a745",
  rejected: "#dc3545", duplicate: "#ffc107", informative: "#6c757d",
  not_applicable: "#dc3545", spam: "#b71c1c",
};
var BUG_STATUS_LABEL = {
  pending: "Pending", triaging: "Triaging", accepted: "Accepted",
  rejected: "Rejected", duplicate: "Duplicate", informative: "Informative",
  not_applicable: "Not Applicable", spam: "Spam",
};

function bugShowForm() {
  var wrap = document.getElementById("bug-form-wrap");
  var toggle = document.getElementById("bug-toggle-form");
  if (wrap) { wrap.style.display = "block"; }
  if (toggle) { toggle.style.display = "none"; }
  var title = document.getElementById("bug-title");
  if (title) { title.focus(); }
}
function bugHideForm() {
  var wrap = document.getElementById("bug-form-wrap");
  var toggle = document.getElementById("bug-toggle-form");
  if (wrap) { wrap.style.display = "none"; }
  if (toggle) { toggle.style.display = "block"; }
}

function bugCommentHtml(c) {
  return (
    '<div class="bug-comment' + (c.staff ? " bug-comment-staff" : "") + '">' +
    '<div class="bug-comment-head">' +
    '<span class="bug-comment-author">' + bugEsc(c.author) + "</span>" +
    (c.staff ? '<span class="bug-comment-badge">STAFF</span>' : "") +
    '<span class="bug-comment-date">' + bugEsc(bugFmtDate(c.date)) + "</span>" +
    "</div>" +
    '<div class="bug-md bug-comment-body">' + (c.content_html || "") + "</div>" +
    "</div>"
  );
}

function bugPostComment(reportId) {
  var input = document.getElementById("bug-reply-input-" + reportId);
  var thread = document.getElementById("bug-thread-" + reportId);
  if (!input || !thread) return;
  var content = (input.value || "").trim();
  if (!content) return;
  var btn = document.querySelector('[data-bugreply="' + reportId + '"]');
  if (btn) btn.disabled = true;

  var fd = new FormData();
  fd.append("nonce", bugNonce());
  fd.append("content", content);
  fetch(bugUrlRoot() + "/bug/reports/" + reportId + "/comments", {
    method: "POST",
    credentials: "same-origin",
    headers: { Accept: "application/json" },
    body: fd,
  })
    .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
    .then(function (res) {
      if (btn) btn.disabled = false;
      if (res.ok && res.j.success) {
        thread.insertAdjacentHTML("beforeend", bugCommentHtml(res.j.data));
        input.value = "";
      } else {
        alert((res.j && res.j.message) || "Could not post reply.");
      }
    })
    .catch(function () {
      if (btn) btn.disabled = false;
      alert("Network error posting reply.");
    });
}

function bugLoadMyReports(container) {
  var challengeId = container.getAttribute("data-challenge");
  var list = container.querySelector(".bug-my-reports-list");
  fetch(bugUrlRoot() + "/bug/reports/mine?challenge_id=" + encodeURIComponent(challengeId), {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
  })
    .then(function (r) { return r.json(); })
    .then(function (resp) {
      var reports = (resp && resp.data) || [];
      if (!reports.length) {
        list.innerHTML = '<small class="text-muted">You have not submitted any reports for this target yet.</small>';
        return;
      }
      var html = "";
      reports.forEach(function (rep) {
        var color = BUG_STATUS[rep.status] || "#6c757d";
        var label = BUG_STATUS_LABEL[rep.status] || rep.status;
        var pts = "";
        if (rep.awarded_value) {
          var neg = rep.awarded_value < 0;
          pts = ' <span class="bug-report-points' + (neg ? " bug-report-points-neg" : "") + '">' +
            (neg ? "" : "+") + rep.awarded_value + " pts</span>";
        }
        var sev = rep.severity ? ' <span class="bug-report-sev">' + bugEsc(rep.severity) + "</span>" : "";
        var evidence = "";
        (rep.evidence || []).forEach(function (e) {
          evidence += '<a href="' + bugEsc(e.url) + '" target="_blank" rel="noopener">' +
            '<img class="bug-evidence-thumb" src="' + bugEsc(e.url) + '" alt="' + bugEsc(e.filename) + '"></a>';
        });
        var dupLine = "";
        if (rep.status === "duplicate" && rep.duplicate_of) {
          dupLine =
            '<div class="bug-report-dup"><i class="fas fa-clone"></i> Duplicate of ' +
            (rep.duplicate_of_title
              ? 'your earlier report <b>#' + rep.duplicate_of + " — " + bugEsc(rep.duplicate_of_title) + "</b>"
              : "an earlier report <b>#" + rep.duplicate_of + "</b>") +
            "</div>";
        }
        var thread = "";
        (rep.comments || []).forEach(function (c) {
          thread += bugCommentHtml(c);
        });
        var threadBox =
          '<h6 class="bug-detail-h">Discussion</h6>' +
          '<div class="bug-thread" id="bug-thread-' + rep.id + '">' + thread + "</div>" +
          '<div class="bug-reply">' +
          '<textarea class="form-control bug-reply-input" id="bug-reply-input-' + rep.id + '" rows="2" placeholder="Reply to the team… (markdown supported)"></textarea>' +
          '<button class="btn bug-reply-btn" data-bugreply="' + rep.id + '"><i class="fas fa-reply"></i> Reply</button>' +
          "</div>";
        var detail =
          '<div class="bug-report-detail" id="bug-detail-' + rep.id + '" style="display:none;">' +
          '<div class="bug-md">' + (rep.description_html || "") + "</div>" +
          (rep.steps_html ? '<h6 class="bug-detail-h">Steps to Reproduce</h6><div class="bug-md">' + rep.steps_html + "</div>" : "") +
          (rep.impact_html ? '<h6 class="bug-detail-h">Impact</h6><div class="bug-md">' + rep.impact_html + "</div>" : "") +
          (evidence ? '<h6 class="bug-detail-h">Evidence</h6><div class="bug-evidence">' + evidence + "</div>" : "") +
          (rep.video_url ? '<h6 class="bug-detail-h">Video</h6><a href="' + bugEsc(rep.video_url) + '" target="_blank" rel="noopener">' + bugEsc(rep.video_url) + "</a>" : "") +
          dupLine +
          (rep.reviewer_notes ? '<div class="bug-report-note"><strong>Reviewer:</strong> ' + bugEsc(rep.reviewer_notes) + "</div>" : "") +
          threadBox +
          '<div class="bug-report-meta">Submitted ' + bugEsc(bugFmtDate(rep.date)) + "</div>" +
          "</div>";
        html +=
          '<div class="bug-report-row">' +
          '<div class="bug-report-row-main" data-bugexpand="' + rep.id + '">' +
          '<span class="bug-report-title">' + bugEsc(rep.title) + "</span>" +
          '<span class="badge bug-report-status" style="background:' + color + ';color:#fff;">' + bugEsc(label) + "</span>" +
          sev + pts +
          '<i class="fas fa-chevron-down bug-chevron"></i>' +
          "</div>" +
          detail +
          "</div>";
      });
      list.innerHTML = html;
    })
    .catch(function () {
      list.innerHTML = '<small class="text-danger">Could not load your reports.</small>';
    });
}

// Load any not-yet-loaded reports panel in scope (guarded by data-loaded).
function bugMaybeLoad(scope) {
  var el = (scope || document).querySelector("#bug-my-reports:not([data-bugloaded])");
  if (el) {
    el.setAttribute("data-bugloaded", "1");
    bugLoadMyReports(el);
  }
}

// Robust: watch the modal for the reports panel being (re)inserted and load it,
// regardless of when Alpine renders the challenge HTML.
function bugInitObserver() {
  var modal = document.getElementById("challenge-window");
  if (!modal) return;
  if (!modal.__bugObs) {
    modal.__bugObs = true;
    var obs = new MutationObserver(function () { bugMaybeLoad(modal); });
    obs.observe(modal, { childList: true, subtree: true });
  }
  bugMaybeLoad(modal);
}

function bugSubmitReport() {
  var btn = document.getElementById("bug-submit");
  var result = document.getElementById("bug-result");
  var challengeId = (document.getElementById("challenge-id") || {}).value;
  var title = (document.getElementById("bug-title") || {}).value || "";
  var description = (document.getElementById("bug-description") || {}).value || "";

  if (!title.trim() || !description.trim()) {
    result.innerHTML = '<div class="alert alert-danger">Title and description are required.</div>';
    return;
  }

  var fd = new FormData();
  fd.append("nonce", bugNonce());
  fd.append("challenge_id", challengeId);
  fd.append("title", title);
  fd.append("description", description);
  fd.append("steps", (document.getElementById("bug-steps") || {}).value || "");
  fd.append("impact", (document.getElementById("bug-impact") || {}).value || "");
  fd.append("video_url", (document.getElementById("bug-video") || {}).value || "");
  var files = (document.getElementById("bug-files") || {}).files || [];
  for (var i = 0; i < files.length; i++) fd.append("screenshot", files[i]);

  btn.disabled = true;
  btn.innerHTML = "Submitting…";
  fetch(bugUrlRoot() + "/bug/reports", {
    method: "POST",
    credentials: "same-origin",
    headers: { Accept: "application/json" },
    body: fd,
  })
    .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
    .then(function (res) {
      btn.disabled = false;
      btn.innerHTML = '<i class="fas fa-paper-plane"></i> Submit Report';
      if (res.ok && res.j.success) {
        ["bug-title", "bug-description", "bug-steps", "bug-impact", "bug-video", "bug-files"].forEach(function (id) {
          var el = document.getElementById(id);
          if (el) el.value = "";
        });
        bugHideForm();
        var toggle = document.getElementById("bug-toggle-form");
        if (toggle) toggle.innerHTML = '<i class="fas fa-bug"></i> Submit another Report';
        result.innerHTML = '<div class="alert alert-success">' + bugEsc(res.j.message) + "</div>";
        var c = document.getElementById("bug-my-reports");
        if (c) bugLoadMyReports(c);
      } else {
        result.innerHTML = '<div class="alert alert-danger">' + bugEsc((res.j && res.j.message) || "Submission failed.") + "</div>";
      }
    })
    .catch(function () {
      btn.disabled = false;
      btn.innerHTML = '<i class="fas fa-paper-plane"></i> Submit Report';
      result.innerHTML = '<div class="alert alert-danger">Network error submitting report.</div>';
    });
}

// Delegated handlers attached once, robust to modal render timing.
if (!window.__bugBountyDelegation) {
  window.__bugBountyDelegation = true;
  bugInitObserver();
  document.addEventListener("click", function (e) {
    var el = e.target.closest ? e.target : null;
    if (!el) return;
    if (el.closest("#bug-submit")) { e.preventDefault(); bugSubmitReport(); return; }
    if (el.closest("#bug-toggle-form")) { e.preventDefault(); bugShowForm(); return; }
    if (el.closest("#bug-cancel")) { e.preventDefault(); bugHideForm(); return; }
    var reply = el.closest("[data-bugreply]");
    if (reply) {
      e.preventDefault();
      bugPostComment(reply.getAttribute("data-bugreply"));
      return;
    }
    var expander = el.closest("[data-bugexpand]");
    if (expander) {
      var id = expander.getAttribute("data-bugexpand");
      var detail = document.getElementById("bug-detail-" + id);
      if (detail) {
        var open = detail.style.display !== "none";
        detail.style.display = open ? "none" : "block";
        expander.classList.toggle("bug-open", !open);
      }
    }
  });
}
