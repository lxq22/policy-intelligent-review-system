"""M3 core business tables.

Revision ID: 20260731_0001
Revises:
Create Date: 2026-07-31
"""

import sqlalchemy as sa
from alembic import op

revision = "20260731_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("name", sa.String(100), nullable=True),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("department", sa.String(150), nullable=True),
        sa.Column("perm_upload", sa.Boolean(), nullable=False),
        sa.Column("perm_delete", sa.Boolean(), nullable=False),
        sa.Column("perm_relation", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(150), nullable=True),
    )
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(150), nullable=True),
    )
    op.create_table(
        "units",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(150), nullable=True),
        sa.Column("level", sa.String(20), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["parent_id"], ["units.id"], ondelete="SET NULL"),
    )
    op.create_table(
        "review_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("record_code", sa.String(255), nullable=False),
        sa.Column("regulation_id", sa.Integer(), nullable=True),
        sa.Column("regulation_name", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_review_records_record_code", "review_records", ["record_code"])
    op.create_index("ix_review_records_regulation_id", "review_records", ["regulation_id"])

    op.create_table(
        "login_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_login_sessions_token_hash", "login_sessions", ["token_hash"], unique=True)

    op.create_table(
        "regulations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("code", sa.String(100), nullable=True),
        sa.Column("department_id", sa.Integer(), nullable=True),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("unit_id", sa.Integer(), nullable=True),
        sa.Column("hierarchy", sa.String(50), nullable=True),
        sa.Column("current_version", sa.String(100), nullable=True),
        sa.Column("publish_date", sa.Date(), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("scope", sa.Text(), nullable=True),
        sa.Column("file_name", sa.String(255), nullable=True),
        sa.Column("parse_status", sa.String(20), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_regulations_name", "regulations", ["name"])
    op.create_index("ix_regulations_deleted_at", "regulations", ["deleted_at"])

    op.create_table(
        "operation_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("operation_type", sa.String(30), nullable=False),
        sa.Column("regulation_id", sa.Integer(), nullable=True),
        sa.Column("regulation_name", sa.String(255), nullable=True),
        sa.Column("operator_id", sa.Integer(), nullable=True),
        sa.Column("operator_name", sa.String(100), nullable=True),
        sa.Column("operated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["operator_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_operation_logs_regulation_id", "operation_logs", ["regulation_id"])

    op.create_table(
        "regulation_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("regulation_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.String(100), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("file_name", sa.String(255), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["regulation_id"], ["regulations.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_regulation_versions_regulation_id", "regulation_versions", ["regulation_id"])

    op.create_table(
        "manual_relations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("relation_type", sa.String(30), nullable=False),
        sa.Column("source_kind", sa.String(30), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["regulations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_id"], ["regulations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_manual_relations_source_id", "manual_relations", ["source_id"])
    op.create_index("ix_manual_relations_target_id", "manual_relations", ["target_id"])

    op.create_table(
        "relation_suggestions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=True),
        sa.Column("target_name", sa.String(255), nullable=True),
        sa.Column("relation_type", sa.String(30), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["regulations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_id"], ["regulations.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_relation_suggestions_source_id", "relation_suggestions", ["source_id"])


def downgrade() -> None:
    op.drop_table("relation_suggestions")
    op.drop_table("manual_relations")
    op.drop_table("regulation_versions")
    op.drop_table("operation_logs")
    op.drop_table("regulations")
    op.drop_table("login_sessions")
    op.drop_table("review_records")
    op.drop_table("units")
    op.drop_table("categories")
    op.drop_table("departments")
    op.drop_table("users")
