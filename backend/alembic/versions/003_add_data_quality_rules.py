"""Add data quality rules and results tables

Revision ID: 003
Revises: 002
Create Date: 2026-08-25 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create data quality rules table
    op.create_table(
        "data_quality_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("data_source", sa.String(255), nullable=True),
        sa.Column("target_field", sa.String(255), nullable=True),
        sa.Column("dimension", sa.String(50), nullable=False, index=True),
        sa.Column("rule_type", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, index=True),
        sa.Column("rule_definition", postgresql.JSON, nullable=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Create data quality results table
    op.create_table(
        "data_quality_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("data_quality_rules.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("execution_timestamp", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("status", sa.String(50), nullable=False, index=True),
        sa.Column("records_checked", sa.Integer, nullable=True),
        sa.Column("records_passed", sa.Integer, nullable=True),
        sa.Column("records_failed", sa.Integer, nullable=True),
        sa.Column("execution_duration_ms", sa.Integer, nullable=True),
        sa.Column("error_details", sa.Text, nullable=True),
        sa.Column("error_stack", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Create index on rule_id + execution_timestamp for efficient historical queries
    op.create_index("ix_dq_results_rule_execution", "data_quality_results", ["rule_id", "execution_timestamp"])


def downgrade() -> None:
    op.drop_index("ix_dq_results_rule_execution")
    op.drop_table("data_quality_results")
    op.drop_table("data_quality_rules")
