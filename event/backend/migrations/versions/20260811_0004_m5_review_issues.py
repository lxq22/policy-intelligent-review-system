"""M5 review issues and human-processing history.

Revision ID: 20260811_0004
Revises: 20260810_0003
Create Date: 2026-08-11
"""

import sqlalchemy as sa
from alembic import op

revision = "20260811_0004"
down_revision = "20260810_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "review_issues",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("review_record_id", sa.Integer(), nullable=False),
        sa.Column("dimension", sa.String(20), nullable=False),
        sa.Column("original", sa.Text(), nullable=False),
        sa.Column("location", sa.String(500), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("consequence", sa.Text(), nullable=False),
        sa.Column("suggestion", sa.Text(), nullable=False),
        sa.Column(
            "insufficient_evidence", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="待处理"),
        sa.Column("opinion", sa.Text(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["review_record_id"], ["review_records.id"], ondelete="CASCADE"
        ),
        sa.CheckConstraint(
            "dimension IN ('semantic', 'rule', 'conflict', 'consistency')",
            name="ck_review_issue_dimension",
        ),
        sa.CheckConstraint(
            "status IN ('待处理', '已采纳', '已忽略')",
            name="ck_review_issue_status",
        ),
    )
    op.create_index(
        "ix_review_issues_review_record_id", "review_issues", ["review_record_id"]
    )
    op.create_index("ix_review_issues_dimension", "review_issues", ["dimension"])

    op.create_table(
        "review_issue_histories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("issue_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("actor_name", sa.String(100), nullable=False),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("opinion", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["issue_id"], ["review_issues.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "action IN ('采纳修改建议', '忽略', '补充处理意见')",
            name="ck_review_issue_history_action",
        ),
    )
    op.create_index(
        "ix_review_issue_histories_issue_id", "review_issue_histories", ["issue_id"]
    )

    # M4 only stored review inputs. They must not appear as completed M5 reports.
    op.execute(sa.text("UPDATE review_records SET completed_at = NULL"))


def downgrade() -> None:
    op.drop_index(
        "ix_review_issue_histories_issue_id", table_name="review_issue_histories"
    )
    op.drop_table("review_issue_histories")
    op.drop_index("ix_review_issues_dimension", table_name="review_issues")
    op.drop_index("ix_review_issues_review_record_id", table_name="review_issues")
    op.drop_table("review_issues")
