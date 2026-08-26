"""Add governance_policies scoped to the domain/dataset hierarchy

Revision ID: 008
Revises: 007
Create Date: 2026-08-26 00:00:00.000000

Migration 006 dropped the old data_asset-scoped governance_policies table.
This recreates it scoped to the real DataDomain/Dataset hierarchy instead.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "governance_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("domain_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("data_domains.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("policy_type", sa.String(100), nullable=False, index=True),
        sa.Column("policy_definition", postgresql.JSON, nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft", index=True),
        sa.Column("effective_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expiration_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("governance_policies")
