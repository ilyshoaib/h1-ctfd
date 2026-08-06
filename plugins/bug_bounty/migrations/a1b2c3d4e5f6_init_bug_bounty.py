"""Create bug_bounty tables (bug_challenge, bug_report)

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-07-24 00:00:00.000000

"""
import sqlalchemy as sa

from CTFd.plugins.migrations import get_all_tables

revision = "a1b2c3d4e5f6"
down_revision = None
branch_labels = None
depends_on = None


def upgrade(op=None):
    tables = get_all_tables(op=op)

    if "bug_challenge" not in tables:
        op.create_table(
            "bug_challenge",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("scope", sa.Text(), nullable=True),
            sa.Column("out_of_scope", sa.Text(), nullable=True),
            sa.Column("reward_low", sa.Integer(), nullable=True),
            sa.Column("reward_medium", sa.Integer(), nullable=True),
            sa.Column("reward_high", sa.Integer(), nullable=True),
            sa.Column("reward_critical", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["id"], ["challenges.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    if "bug_report" not in tables:
        op.create_table(
            "bug_report",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("challenge_id", sa.Integer(), nullable=True),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("team_id", sa.Integer(), nullable=True),
            sa.Column("title", sa.String(length=256), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("steps", sa.Text(), nullable=True),
            sa.Column("impact", sa.Text(), nullable=True),
            sa.Column("video_url", sa.Text(), nullable=True),
            sa.Column("evidence", sa.JSON(), nullable=True),
            sa.Column("severity", sa.String(length=32), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=True),
            sa.Column("awarded_value", sa.Integer(), nullable=True),
            sa.Column("award_id", sa.Integer(), nullable=True),
            sa.Column("reviewer_notes", sa.Text(), nullable=True),
            sa.Column("date", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(
                ["challenge_id"], ["challenges.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["award_id"], ["awards.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade(op=None):
    tables = get_all_tables(op=op)
    if "bug_report" in tables:
        op.drop_table("bug_report")
    if "bug_challenge" in tables:
        op.drop_table("bug_challenge")
