from datetime import datetime

from CTFd.models import Challenges, Files, db


class BugReportFile(Files):
    """Registers the "bug_report" polymorphic identity for evidence uploads.
    Without it, CTFd's polymorphic Files query raises "No such
    polymorphic_identity 'bug_report'" when loading these rows (e.g. the admin
    Files page). Single-table subclass — no extra columns."""

    __mapper_args__ = {"polymorphic_identity": "bug_report"}


class BugChallenge(Challenges):
    """A "bug bounty" target. Behaves like a normal challenge for listing/board
    purposes but is never flag-solved — hunters submit reports (BugReport) that
    admins triage and award manually. Joined-table subclass, identity "bug"."""

    __mapper_args__ = {"polymorphic_identity": "bug"}
    id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), primary_key=True
    )
    scope = db.Column(db.Text)
    out_of_scope = db.Column(db.Text)
    reward_low = db.Column(db.Integer, default=0)
    reward_medium = db.Column(db.Integer, default=0)
    reward_high = db.Column(db.Integer, default=0)
    reward_critical = db.Column(db.Integer, default=0)

    def __init__(self, *args, **kwargs):
        super(BugChallenge, self).__init__(**kwargs)
        # Bug targets are scored via Awards, not the challenge value.
        if self.value is None:
            self.value = 0
        if self.function is None:
            self.function = "static"


class BugReport(db.Model):
    """A vulnerability report submitted by a hunter against a BugChallenge."""

    __tablename__ = "bug_report"
    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE")
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"))
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id", ondelete="CASCADE"))

    title = db.Column(db.String(256))
    description = db.Column(db.Text)
    steps = db.Column(db.Text)
    impact = db.Column(db.Text)
    video_url = db.Column(db.Text)
    # list of {"file_id": int, "location": str, "filename": str}
    evidence = db.Column(db.JSON)

    severity = db.Column(db.String(32))  # low / medium / high / critical
    # pending / triaging / accepted / rejected / duplicate / informative /
    # not_applicable / spam
    status = db.Column(db.String(32), default="pending")
    # When status == "duplicate": id of the earlier report this duplicates.
    duplicate_of = db.Column(db.Integer)
    awarded_value = db.Column(db.Integer, default=0)
    award_id = db.Column(db.Integer, db.ForeignKey("awards.id", ondelete="SET NULL"))
    reviewer_notes = db.Column(db.Text)
    date = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, *args, **kwargs):
        super(BugReport, self).__init__(**kwargs)


class BugComment(db.Model):
    """A message in the hunter <-> admin thread on a report."""

    __tablename__ = "bug_comment"
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(
        db.Integer, db.ForeignKey("bug_report.id", ondelete="CASCADE")
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"))
    staff = db.Column(db.Boolean, default=False)  # author was an admin
    content = db.Column(db.Text)
    date = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, *args, **kwargs):
        super(BugComment, self).__init__(**kwargs)


class BugNotification(db.Model):
    """A private, per-hunter toast (e.g. a report status change). Kept separate
    from CTFd's global Notifications so it is only ever delivered to its owner
    and never pollutes the site-wide notification stream / unread counter."""

    __tablename__ = "bug_notification"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"))
    report_id = db.Column(
        db.Integer, db.ForeignKey("bug_report.id", ondelete="CASCADE")
    )
    title = db.Column(db.String(128))
    message = db.Column(db.String(256))
    status = db.Column(db.String(32))
    seen = db.Column(db.Boolean, default=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, *args, **kwargs):
        super(BugNotification, self).__init__(**kwargs)
