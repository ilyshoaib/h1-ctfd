from flask import Blueprint, request

from CTFd.models import db
from CTFd.plugins import (
    register_admin_plugin_menu_bar,
    register_plugin_assets_directory,
    register_plugin_script,
)
from CTFd.plugins.challenges import (
    CHALLENGE_CLASSES,
    BaseChallenge,
    ChallengeResponse,
)
from CTFd.plugins.migrations import upgrade

from .models import (  # noqa: F401
    BugChallenge,
    BugNotification,
    BugReportFile,
    BugReport,
)

REWARD_FIELDS = ("reward_low", "reward_medium", "reward_high", "reward_critical")


def _form_data(req):
    """Return a mutable dict from either a JSON body or a form post."""
    data = req.get_json(silent=True)
    if data is None:
        data = req.form.to_dict()
    else:
        data = dict(data)
    return data


def _coerce_ints(data):
    for key in REWARD_FIELDS + ("value",):
        if key in data and data[key] not in (None, ""):
            try:
                data[key] = int(data[key])
            except (ValueError, TypeError):
                data[key] = 0
    return data


class BugChallengeType(BaseChallenge):
    id = "bug"
    name = "bug"
    templates = {
        "create": "/plugins/bug_bounty/assets/create.html",
        "update": "/plugins/bug_bounty/assets/update.html",
        "view": "/plugins/bug_bounty/assets/view.html",
    }
    scripts = {
        "create": "/plugins/bug_bounty/assets/create.js",
        "update": "/plugins/bug_bounty/assets/update.js",
        "view": "/plugins/bug_bounty/assets/view.js",
    }
    route = "/plugins/bug_bounty/assets/"
    blueprint = Blueprint(
        "bug_bounty_assets",
        __name__,
        template_folder="templates",
        static_folder="assets",
    )
    challenge_model = BugChallenge

    @classmethod
    def create(cls, request):
        data = _coerce_ints(_form_data(request))
        data.setdefault("value", 0)
        data.setdefault("function", "static")
        challenge = cls.challenge_model(**data)
        db.session.add(challenge)
        db.session.commit()
        return challenge

    @classmethod
    def read(cls, challenge):
        challenge = BugChallenge.query.filter_by(id=challenge.id).first()
        data = super().read(challenge)
        data.update(
            {
                "scope": challenge.scope,
                "out_of_scope": challenge.out_of_scope,
                "reward_low": challenge.reward_low,
                "reward_medium": challenge.reward_medium,
                "reward_high": challenge.reward_high,
                "reward_critical": challenge.reward_critical,
            }
        )
        return data

    @classmethod
    def update(cls, challenge, request):
        data = _coerce_ints(_form_data(request))
        for attr, value in data.items():
            setattr(challenge, attr, value)
        db.session.commit()
        return challenge

    @classmethod
    def attempt(cls, challenge, request):
        # Bug targets are not flag-solvable; hunters use the report form.
        return ChallengeResponse(
            status="incorrect",
            message="This is a bug bounty target — submit your findings using the report form.",
        )


def load(app):
    upgrade(plugin_name="bug_bounty")
    CHALLENGE_CLASSES["bug"] = BugChallengeType
    register_plugin_assets_directory(
        app, base_path="/plugins/bug_bounty/assets/"
    )
    from .views import bug_bp

    app.register_blueprint(bug_bp)
    register_admin_plugin_menu_bar("Bug Reports", "/admin/bug-reports")
    # Site-wide script that delivers private per-hunter report-status toasts.
    register_plugin_script("/plugins/bug_bounty/assets/notify.js")

    # This platform runs in user-only mode. If a stale/cached link (e.g. a
    # redirect cached from a previous teams-mode config) sends someone to a
    # /team(s) URL, send them to the programs board instead of a dead 404.
    @app.before_request
    def _redirect_stale_team_urls():
        from flask import redirect, url_for
        from CTFd.utils.config import is_teams_mode

        if is_teams_mode():
            return None
        path = (request.path or "").rstrip("/").lower()
        if path in ("/team", "/teams"):
            return redirect(url_for("challenges.listing"))
        return None

    # Opening the notifications center marks this hunter's bug notifications as
    # read (clears the bell badge). History still shows via the context
    # processor below.
    @app.before_request
    def _mark_bug_notifications_read():
        from CTFd.models import db
        from CTFd.utils.user import authed, get_current_user

        if (request.path or "").rstrip("/").lower() != "/notifications":
            return None
        if not authed():
            return None
        user = get_current_user()
        if user is not None:
            (
                BugNotification.query.filter_by(user_id=user.id, seen=False).update(
                    {"seen": True}
                )
            )
            db.session.commit()
        return None

    # Hunter stats for profile pages (users/public.html + users/private.html
    # call this as a Jinja global; they guard with `is defined`).
    def bug_hunter_stats(user_id):
        reports = BugReport.query.filter_by(user_id=user_id).all()
        total = len(reports)
        accepted = [r for r in reports if r.status == "accepted"]
        sev = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for r in accepted:
            if r.severity in sev:
                sev[r.severity] += 1
        reputation = sum(r.awarded_value or 0 for r in reports)
        return {
            "total": total,
            "accepted": len(accepted),
            "rate": int(round(len(accepted) * 100.0 / total)) if total else 0,
            "reputation": reputation,
            "severities": sev,
        }

    app.jinja_env.globals["bug_hunter_stats"] = bug_hunter_stats

    # Expose this hunter's bug notifications to every template so the core
    # notifications center can list them.
    @app.context_processor
    def _inject_bug_notifications():
        from CTFd.utils.user import authed, get_current_user

        if not authed():
            return {}
        user = get_current_user()
        if user is None:
            return {}
        notes = (
            BugNotification.query.filter_by(user_id=user.id)
            .order_by(BugNotification.id.desc())
            .limit(50)
            .all()
        )
        return {"bug_notifications": notes}
