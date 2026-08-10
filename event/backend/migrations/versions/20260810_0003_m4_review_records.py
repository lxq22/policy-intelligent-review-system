"""M4 immutable review-input records.

Revision ID: 20260810_0003
Revises: 20260810_0002
Create Date: 2026-08-10
"""

import sqlalchemy as sa
from alembic import op

revision = "20260810_0003"
down_revision = "20260810_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_review_records_record_code", table_name="review_records")
    with op.batch_alter_table("review_records") as batch:
        batch.add_column(sa.Column("temporary_file_id", sa.Integer(), nullable=True))
        batch.add_column(
            sa.Column("source_type", sa.String(20), nullable=False, server_default="regulation")
        )
        batch.add_column(sa.Column("dimensions", sa.JSON(), nullable=False, server_default="[]"))
        batch.add_column(
            sa.Column("source_snapshot", sa.JSON(), nullable=False, server_default="[]")
        )
        batch.add_column(
            sa.Column("candidate_snapshot", sa.JSON(), nullable=False, server_default="[]")
        )
        batch.add_column(sa.Column("created_by", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("completed_at", sa.DateTime(), nullable=True))
        batch.create_foreign_key(
            "fk_review_records_temporary_file",
            "temporary_review_files",
            ["temporary_file_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_foreign_key(
            "fk_review_records_created_by",
            "users",
            ["created_by"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_index(
        "ix_review_records_record_code", "review_records", ["record_code"], unique=True
    )
    op.create_index(
        "ix_review_records_temporary_file_id", "review_records", ["temporary_file_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_review_records_temporary_file_id", table_name="review_records")
    op.drop_index("ix_review_records_record_code", table_name="review_records")
    with op.batch_alter_table("review_records") as batch:
        batch.drop_constraint("fk_review_records_created_by", type_="foreignkey")
        batch.drop_constraint("fk_review_records_temporary_file", type_="foreignkey")
        batch.drop_column("completed_at")
        batch.drop_column("created_by")
        batch.drop_column("candidate_snapshot")
        batch.drop_column("source_snapshot")
        batch.drop_column("dimensions")
        batch.drop_column("source_type")
        batch.drop_column("temporary_file_id")
    op.create_index(
        "ix_review_records_record_code", "review_records", ["record_code"], unique=False
    )
