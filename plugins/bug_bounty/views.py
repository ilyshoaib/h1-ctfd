import os

from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for

from CTFd.cache import clear_standings
from CTFd.models import Awards, Challenges, Files, Teams, Users, db
from CTFd.utils.config import is_teams_mode
from CTFd.utils.config.pages import build_markdown
from CTFd.utils.decorators import admins_only, authed_only, ratelimit
from CTFd.utils.uploads import get_uploader, upload_file
from CTFd.utils.user import get_current_team, get_current_user, is_admin

from .models import BugChallenge, BugComment, BugNotification, BugReport

bug_bp = Blueprint("bug_bounty", __name__, template_folder="templates")

SEVERITIES = ["low", "medium", "high", "critical"]
STATUSES = [
    "pending", "triaging", "accepted", "rejected", "duplicate", "informative",
    "not_applicable", "spam",
]
# Statuses that deduct points (negative award) instead of granting them
PENALTY_STATUSES = {"not_applicable", "spam"}
STATUS_LABELS = {
    "pending": "Pending",
    "triaging": "Triaging",
    "accepted": "Accepted",
    "rejected": "Rejected",
    "duplicate": "Duplicate",
    "informative": "Informative",
    "not_applicable": "Not Applicable",
    "spam": "Spam",
}

ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_FILES = 5


def md(text):
    """Render user-supplied markdown to sanitized HTML (safe for admins to view)."""
    return build_markdown(text or "", sanitize=True)


def report_to_dict(r):
    return {
        "id": r.id,
        "challenge_id": r.challenge_id,
        "title": r.title,
        "status": r.status or "pending",
        "severity": r.severity,
        "awarded_value": r.awarded_value or 0,
        "reviewer_notes": r.reviewer_notes,
        "date": r.date.isoformat() if r.date else None,
    }


def comment_to_dict(c):
    author = Users.query.filter_by(id=c.user_id).first()
    return {
        "id": c.id,
        "author": author.name if author else "—",
        "staff": bool(c.staff),
        "content_html": md(c.content),
        "date": c.date.isoformat() if c.date else None,
    }


def report_comments(report_id):
    comments = (
        BugComment.query.filter_by(report_id=report_id)
        .order_by(BugComment.id.asc())
        .all()
    )
    return [comment_to_dict(c) for c in comments]


def report_detail_dict(r):
    """Full report incl. rendered markdown + evidence URLs, for viewing."""
    evidence = []
    for e in r.evidence or []:
        fid = (e or {}).get("file_id")
        if fid:
            from flask import url_for

            evidence.append(
                {
                    "url": url_for("bug_bounty.report_file", file_id=fid),
                    "filename": (e or {}).get("filename"),
                }
            )
    # Duplicate linkage: always show the id; show the original's title only if
    # the same account owns it (don't leak other hunters' report titles).
    duplicate_of_title = None
    if r.duplicate_of:
        orig = BugReport.query.filter_by(id=r.duplicate_of).first()
        if orig and orig.user_id == r.user_id:
            duplicate_of_title = orig.title
    d = report_to_dict(r)
    d.update(
        {
            "description_html": md(r.description),
            "steps_html": md(r.steps) if r.steps else "",
            "impact_html": md(r.impact) if r.impact else "",
            "video_url": r.video_url,
            "evidence": evidence,
            "duplicate_of": r.duplicate_of,
            "duplicate_of_title": duplicate_of_title,
            "comments": report_comments(r.id),
        }
    )
    return d


def _owned_by_requester(query):
    """Restrict a BugReport query to the current account (team or user)."""
    team = get_current_team()
    if team:
        return query.filter(BugReport.team_id == team.id)
    return query.filter(BugReport.user_id == get_current_user().id)


@bug_bp.route("/bug/reports", methods=["POST"])
@authed_only
@ratelimit(method="POST", limit=15, interval=60)
def submit_report():
    challenge_id = request.form.get("challenge_id")
    chal = BugChallenge.query.filter_by(id=challenge_id).first()
    if chal is None or chal.state == "hidden":
        return jsonify({"success": False, "message": "Invalid target."}), 404

    title = (request.form.get("title") or "").strip()
    description = (request.form.get("description") or "").strip()
    if not title or not description:
        return (
            jsonify({"success": False, "message": "Title and description are required."}),
            400,
        )

    video_url = (request.form.get("video_url") or "").strip()
    if video_url and not video_url.lower().startswith(("http://", "https://")):
        return (
            jsonify({"success": False, "message": "Video URL must start with http:// or https://"}),
            400,
        )

    user = get_current_user()
    team = get_current_team()

    report = BugReport(
        challenge_id=chal.id,
        user_id=user.id,
        team_id=team.id if team else None,
        title=title[:256],
        description=description,
        steps=request.form.get("steps") or None,
        impact=request.form.get("impact") or None,
        video_url=video_url or None,
        status="pending",
        awarded_value=0,
        evidence=[],
    )
    db.session.add(report)
    db.session.commit()

    # Store screenshot evidence (images only, size-capped)
    evidence = []
    files = [f for f in request.files.getlist("screenshot") if f and f.filename]
    for f in files[:MAX_FILES]:
        ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
        if ext not in ALLOWED_IMAGE_EXT:
            continue
        f.seek(0, os.SEEK_END)
        size = f.tell()
        f.seek(0)
        if size > MAX_FILE_BYTES:
            continue
        file_row = upload_file(file=f, type="bug_report")
        evidence.append(
            {"file_id": file_row.id, "location": file_row.location, "filename": f.filename}
        )

    report.evidence = evidence
    db.session.commit()

    return jsonify(
        {
            "success": True,
            "message": "Report submitted — pending review.",
            "data": report_to_dict(report),
        }
    )


@bug_bp.route("/bug/reports/mine", methods=["GET"])
@authed_only
def my_reports():
    challenge_id = request.args.get("challenge_id")
    if not challenge_id:
        return jsonify({"success": True, "data": []})
    q = _owned_by_requester(BugReport.query.filter_by(challenge_id=challenge_id))
    reports = q.order_by(BugReport.id.desc()).all()
    return jsonify({"success": True, "data": [report_detail_dict(r) for r in reports]})


@bug_bp.route("/bug/reports/files/<int:file_id>", methods=["GET"])
@authed_only
def report_file(file_id):
    f = Files.query.filter_by(id=file_id).first_or_404()

    if not is_admin():
        # Only the submitting account may view its own evidence
        owned = _owned_by_requester(BugReport.query).all()
        allowed = any(
            file_id == (e or {}).get("file_id")
            for r in owned
            for e in (r.evidence or [])
        )
        if not allowed:
            abort(403)

    return get_uploader().download(f.location)


@bug_bp.route("/bug/reports/<int:report_id>/comments", methods=["POST"])
@authed_only
@ratelimit(method="POST", limit=30, interval=60)
def post_comment(report_id):
    r = BugReport.query.filter_by(id=report_id).first_or_404()

    # Only the report's owner or an admin may participate in the thread.
    admin = is_admin()
    if not admin:
        owned = _owned_by_requester(BugReport.query.filter_by(id=report_id)).first()
        if owned is None:
            abort(403)

    content = (request.form.get("content") or "").strip()
    if not content:
        return jsonify({"success": False, "message": "Comment cannot be empty."}), 400

    user = get_current_user()
    comment = BugComment(
        report_id=r.id, user_id=user.id, staff=admin, content=content[:5000]
    )
    db.session.add(comment)
    db.session.commit()

    # An admin reply pings the hunter privately (their own comments don't).
    if admin and r.user_id and r.user_id != user.id:
        chal = Challenges.query.filter_by(id=r.challenge_id).first()
        program = chal.name if chal else "your target"
        note = BugNotification(
            user_id=r.user_id,
            report_id=r.id,
            title="New reply",
            message='New reply on your "%s" report.' % program,
            status="comment",
        )
        db.session.add(note)
        db.session.commit()

    # The admin detail page posts a normal form and expects a redirect back.
    if request.form.get("redirect"):
        return redirect(url_for("bug_bounty.admin_report_detail", report_id=r.id))
    return jsonify({"success": True, "data": comment_to_dict(comment)})


# ------------------------------------------------------------------ admin ---
def _account_name(report):
    if is_teams_mode():
        t = Teams.query.filter_by(id=report.team_id).first()
        return t.name if t else "—"
    u = Users.query.filter_by(id=report.user_id).first()
    return u.name if u else "—"


@bug_bp.route("/admin/bug-reports", methods=["GET"])
@admins_only
def admin_reports():
    active_status = request.args.get("status") or None
    q = BugReport.query
    if active_status:
        q = q.filter_by(status=active_status)
    reports = q.order_by(BugReport.id.desc()).all()
    rows = []
    for r in reports:
        chal = Challenges.query.filter_by(id=r.challenge_id).first()
        rows.append(
            {"r": r, "target": chal.name if chal else "—", "account": _account_name(r)}
        )
    counts = {s: BugReport.query.filter_by(status=s).count() for s in STATUSES}
    counts["all"] = BugReport.query.count()
    return render_template(
        "admin/bug_reports.html",
        rows=rows,
        statuses=STATUSES,
        status_labels=STATUS_LABELS,
        counts=counts,
        active_status=active_status,
    )


@bug_bp.route("/admin/bug-reports/<int:report_id>", methods=["GET"])
@admins_only
def admin_report_detail(report_id):
    r = BugReport.query.filter_by(id=report_id).first_or_404()
    chal = BugChallenge.query.filter_by(id=r.challenge_id).first()
    if chal is None:
        chal = Challenges.query.filter_by(id=r.challenge_id).first()
    duplicate_original = (
        BugReport.query.filter_by(id=r.duplicate_of).first() if r.duplicate_of else None
    )
    return render_template(
        "admin/bug_report_detail.html",
        report=r,
        challenge=chal,
        account=_account_name(r),
        severities=SEVERITIES,
        statuses=STATUSES,
        status_labels=STATUS_LABELS,
        penalty_statuses=list(PENALTY_STATUSES),
        description_html=md(r.description),
        steps_html=md(r.steps) if r.steps else "",
        impact_html=md(r.impact) if r.impact else "",
        comments=report_comments(r.id),
        duplicate_original=duplicate_original,
    )


@bug_bp.route("/admin/bug-reports/<int:report_id>/review", methods=["POST"])
@admins_only
def admin_report_review(report_id):
    r = BugReport.query.filter_by(id=report_id).first_or_404()
    previous_status = r.status

    status = request.form.get("status") or "pending"
    if status not in STATUSES:
        abort(400, description="Invalid status.")
    severity = request.form.get("severity") or None
    if severity is not None and severity not in SEVERITIES:
        abort(400, description="Invalid severity.")
    try:
        points = int(request.form.get("awarded_value") or 0)
    except (ValueError, TypeError):
        points = 0
    notes = request.form.get("reviewer_notes") or None

    # Duplicate linking: only meaningful when status is "duplicate".
    duplicate_of = None
    if status == "duplicate":
        raw = (request.form.get("duplicate_of") or "").strip().lstrip("#")
        if raw:
            try:
                duplicate_of = int(raw)
            except (ValueError, TypeError):
                abort(400, description="Duplicate-of must be a report id.")
            if duplicate_of == r.id:
                abort(400, description="A report cannot duplicate itself.")
            if BugReport.query.filter_by(id=duplicate_of).first() is None:
                abort(400, description="No such report to mark as original.")

    r.status = status
    r.severity = severity
    r.reviewer_notes = notes
    r.duplicate_of = duplicate_of

    # Reconcile any previously-created award so scores never double-count
    if r.award_id:
        old = Awards.query.filter_by(id=r.award_id).first()
        if old:
            db.session.delete(old)
        r.award_id = None
        r.awarded_value = 0

    # Decide the award value: accepted grants points; penalty statuses (spam /
    # not applicable) deduct them (a negative award, forced negative regardless
    # of the sign the admin typed).
    value = 0
    if status == "accepted" and points > 0:
        value = points
    elif status in PENALTY_STATUSES and points != 0:
        value = -abs(points)

    if value != 0:
        award = Awards(
            user_id=r.user_id,
            team_id=r.team_id,
            name=("Bug: " + (r.title or "report"))[:80],
            description="Bug bounty report #%d" % r.id,
            value=value,
            category="Bug Bounty",
        )
        db.session.add(award)
        db.session.commit()
        r.award_id = award.id
        r.awarded_value = value

    db.session.commit()
    clear_standings()

    # Ping the hunter (privately) when their report's status actually changes.
    if status != previous_status and r.user_id:
        chal = Challenges.query.filter_by(id=r.challenge_id).first()
        program = chal.name if chal else "your target"
        label = STATUS_LABELS.get(status, status)
        note = BugNotification(
            user_id=r.user_id,
            report_id=r.id,
            title="Report update",
            message='Your "%s" report was marked %s.' % (program, label),
            status=status,
        )
        db.session.add(note)
        db.session.commit()

    return redirect(url_for("bug_bounty.admin_report_detail", report_id=r.id))


@bug_bp.route("/bug/notifications", methods=["GET"])
@authed_only
def bug_notifications():
    """This hunter's private notifications (newest first) + unread count, for
    the live toast poller and the bell badge. `seen` means "read in the
    notifications center"; it is cleared only when the center is opened, not by
    this read — so the history persists. Toast de-duplication is done client
    side (by highest-id-seen), independent of `seen`."""
    user = get_current_user()
    notes = (
        BugNotification.query.filter_by(user_id=user.id)
        .order_by(BugNotification.id.desc())
        .limit(50)
        .all()
    )
    unread = BugNotification.query.filter_by(user_id=user.id, seen=False).count()
    data = [
        {
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "status": n.status,
            "date": n.date.isoformat() if n.date else None,
        }
        for n in notes
    ]
    return jsonify({"success": True, "data": data, "unread": unread})
