"""Add bug_notification table (private per-hunter toasts)

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-24 00:00:00.000000

"""
import sqlalchemy as sa

from CTFd.plugins.migrations import get_all_tables

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade(op=None):
    tables = get_all_tables(op=op)

    if "bug_notification" not in tables:
        op.create_table(
            "bug_notification",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("report_id", sa.Integer(), nullable=True),
            sa.Column("title", sa.String(length=128), nullable=True),
            sa.Column("message", sa.String(length=256), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=True),
            sa.Column("seen", sa.Boolean(), nullable=True),
            sa.Column("date", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["report_id"], ["bug_report.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade(op=None):
    tables = get_all_tables(op=op)
    if "bug_notification" in tables:
        op.drop_table("bug_notification")
