"""Make datasets.domain_id optional

A dataset should not be forced into one of a handful of predefined domains
at creation time - it can belong to no domain yet, or to a domain that
doesn't exist in the system when it's first uploaded. Domain assignment
becomes something that can be set, changed, or cleared at any time via
PATCH /api/v1/datasets/{id}/domain, rather than a mandatory, one-time
choice at upload.

Revision ID: 010
Revises: 009
Create Date: 2026-08-26 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("datasets", "domain_id", existing_type=sa.dialects.postgresql.UUID(as_uuid=True), nullable=True)


def downgrade() -> None:
    # Any dataset left without a domain would violate the restored NOT NULL
    # constraint, so downgrading requires the operator to first assign one.
    op.alter_column("datasets", "domain_id", existing_type=sa.dialects.postgresql.UUID(as_uuid=True), nullable=False)
