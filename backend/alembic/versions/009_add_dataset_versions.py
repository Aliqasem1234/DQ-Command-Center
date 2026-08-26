"""Add dataset_versions for uploaded file storage, profiling, and cleaning history

Revision ID: 009
Revises: 008
Create Date: 2026-08-26 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dataset_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=True),
        sa.Column("file_format", sa.String(20), nullable=False),
        sa.Column("file_size_bytes", sa.Integer, nullable=True),
        sa.Column("row_count", sa.Integer, nullable=True),
        sa.Column("column_count", sa.Integer, nullable=True),
        sa.Column("is_original", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("source_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cleaning_operations", postgresql.JSON, nullable=True),
        sa.Column("rows_changed", sa.Integer, nullable=True),
        sa.Column("values_changed", sa.Integer, nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="uploaded", index=True),
        sa.Column("quality_score", sa.Float, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("dataset_id", "version_number", name="uq_dataset_version_number"),
    )
    op.create_foreign_key(
        "fk_dataset_version_source", "dataset_versions", "dataset_versions",
        ["source_version_id"], ["id"], ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_dataset_version_source", "dataset_versions", type_="foreignkey")
    op.drop_table("dataset_versions")
