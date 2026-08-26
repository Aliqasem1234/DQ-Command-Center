"""Add metadata tables

Revision ID: 005
Revises: 004
Create Date: 2026-08-25 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create metadata table
    op.create_table(
        "metadata",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("data_asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("data_assets.id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("data_type", sa.String(50), nullable=False),
        sa.Column("nullable", sa.Boolean(), default=True, nullable=False),
        sa.Column("default_value", sa.String(255), nullable=True),
        sa.Column("column_position", sa.Integer, nullable=True),
        sa.Column("is_primary_key", sa.Boolean(), default=False, nullable=False),
        sa.Column("is_foreign_key", sa.Boolean(), default=False, nullable=False),
        sa.Column("value_count", sa.Integer, nullable=True),
        sa.Column("null_count", sa.Integer, nullable=True),
        sa.Column("unique_count", sa.Integer, nullable=True),
        sa.Column("duplicate_count", sa.Integer, nullable=True),
        sa.Column("min_value", sa.String(255), nullable=True),
        sa.Column("max_value", sa.String(255), nullable=True),
        sa.Column("average_length", sa.Float, nullable=True),
        sa.Column("completeness_score", sa.Float, nullable=True),
        sa.Column("validity_score", sa.Float, nullable=True),
        sa.Column("uniqueness_score", sa.Float, nullable=True),
        sa.Column("business_term", sa.String(255), nullable=True),
        sa.Column("business_definition", sa.Text, nullable=True),
        sa.Column("steward_notes", sa.Text, nullable=True),
        sa.Column("example_values", postgresql.JSON, nullable=True),
        sa.Column("format_validation", sa.String(255), nullable=True),
        sa.Column("allowed_values", postgresql.JSON, nullable=True),
        sa.Column("regex_pattern", sa.String(500), nullable=True),
        sa.Column("last_profiled", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Create metadata_tags table
    op.create_table(
        "metadata_tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("metadata_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("metadata.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("tag", sa.String(100), nullable=False),
        sa.Column("category", sa.String(100), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("metadata_tags")
    op.drop_table("metadata")
