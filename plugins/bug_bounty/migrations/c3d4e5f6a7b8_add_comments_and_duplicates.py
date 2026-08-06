"""Add bug_comment table and bug_report.duplicate_of

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-24 00:00:00.000000

"""
import sqlalchemy as sa

from CTFd.plugins.migrations import get_all_tables

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def _get_columns(op, table):
    from sqlalchemy import inspect

    conn = op.get_bind()
    return [c["name"] for c in inspect(conn).get_columns(table)]


def upgrade(op=None):
    tables = get_all_tables(op=op)

    if "bug_comment" not in tables:
        op.create_table(
            "bug_comment",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("report_id", sa.Integer(), nullable=True),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("staff", sa.Boolean(), nullable=True),
            sa.Column("content", sa.Text(), nullable=True),
            sa.Column("date", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(
                ["report_id"], ["bug_report.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    if "bug_report" in tables and "duplicate_of" not in _get_columns(op, "bug_report"):
        op.add_column(
            "bug_report", sa.Column("duplicate_of", sa.Integer(), nullable=True)
        )


def downgrade(op=None):
    tables = get_all_tables(op=op)
    if "bug_comment" in tables:
        op.drop_table("bug_comment")
    if "bug_report" in tables and "duplicate_of" in _get_columns(op, "bug_report"):
        op.drop_column("bug_report", "duplicate_of")
