"""M4 document files, parsing state, clauses, and vectors.

Revision ID: 20260810_0002
Revises: 20260731_0001
Create Date: 2026-08-10
"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "20260810_0002"
down_revision = "20260731_0001"
branch_labels = None
depends_on = None


PARSE_STATUS = "parse_status IN ('待解析', '解析中', '解析成功', '解析失败')"


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    with op.batch_alter_table("regulation_versions") as batch:
        batch.add_column(sa.Column("stored_path", sa.String(500), nullable=True))
        batch.add_column(sa.Column("mime_type", sa.String(150), nullable=True))
        batch.add_column(sa.Column("file_size", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("sha256", sa.String(64), nullable=True))
        batch.add_column(
            sa.Column("parse_status", sa.String(20), nullable=False, server_default="待解析")
        )
        batch.add_column(sa.Column("parse_error", sa.Text(), nullable=True))
        batch.add_column(sa.Column("parsed_at", sa.DateTime(), nullable=True))
        batch.create_check_constraint("ck_regulation_version_parse_status", PARSE_STATUS)

    op.create_table(
        "temporary_review_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("original_name", sa.String(255), nullable=False),
        sa.Column("stored_path", sa.String(500), nullable=False, unique=True),
        sa.Column("mime_type", sa.String(150), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("parse_status", sa.String(20), nullable=False, server_default="待解析"),
        sa.Column("parse_error", sa.Text(), nullable=True),
        sa.Column("parsed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(PARSE_STATUS, name="ck_temporary_file_parse_status"),
    )

    vector_type = Vector(256) if op.get_bind().dialect.name == "postgresql" else sa.JSON()
    op.create_table(
        "clauses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("regulation_version_id", sa.Integer(), nullable=True),
        sa.Column("temporary_file_id", sa.Integer(), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("original_no", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False, server_default=""),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("level", sa.String(30), nullable=False, server_default="article"),
        sa.Column("heading_path", sa.JSON(), nullable=False),
        sa.Column("paragraph_start", sa.Integer(), nullable=False),
        sa.Column("paragraph_end", sa.Integer(), nullable=False),
        sa.Column("embedding", vector_type, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["regulation_version_id"], ["regulation_versions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["temporary_file_id"], ["temporary_review_files.id"], ondelete="CASCADE"
        ),
        sa.CheckConstraint(
            "(regulation_version_id IS NOT NULL AND temporary_file_id IS NULL) OR "
            "(regulation_version_id IS NULL AND temporary_file_id IS NOT NULL)",
            name="ck_clause_exactly_one_source",
        ),
    )
    op.create_index("ix_clauses_regulation_version_id", "clauses", ["regulation_version_id"])
    op.create_index("ix_clauses_temporary_file_id", "clauses", ["temporary_file_id"])


def downgrade() -> None:
    op.drop_table("clauses")
    op.drop_table("temporary_review_files")
    with op.batch_alter_table("regulation_versions") as batch:
        batch.drop_constraint("ck_regulation_version_parse_status", type_="check")
        batch.drop_column("parsed_at")
        batch.drop_column("parse_error")
        batch.drop_column("parse_status")
        batch.drop_column("sha256")
        batch.drop_column("file_size")
        batch.drop_column("mime_type")
        batch.drop_column("stored_path")
