"""Every registered user gets the full product; domains become per-user

Product direction: anyone who registers can use the whole Data Quality
product on their own data, while platform administration stays separate.

1. data_domains gets an owner. Domains are how a user groups *their*
   datasets, so names are unique per owner instead of globally (a global
   unique name let one user block - and detect - another user's "Finance").
   Existing domains get the owner recorded in their CREATE audit entry.
2. The "User" role (given to every new account) receives the product
   permissions: managing datasets, data quality and governance on the
   user's own data, plus analytics and reports. Row-level isolation is
   enforced separately (app.core.dataset_access), so these permissions
   never reach anyone else's data.
3. "Manager" loses audit:view. That permission reads the *global* audit log
   of every user, which is platform administration, not product use; every
   user can instead read their own activity (GET /api/v1/audit/my-logs).

Revision ID: 012
Revises: 011
Create Date: 2026-10-16 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

USER_PRODUCT_PERMISSIONS = [
    "datasets:manage",
    "data_quality:manage",
    "data_governance:manage",
    "analytics:view",
    "reports:create",
    "reports:export",
]


def upgrade() -> None:
    # 4. Each scan run records the dataset quality score it produced, so the
    #    trend shows quality over time (not the share of checks passing).
    op.add_column("quality_check_runs", sa.Column("quality_score", sa.Float(), nullable=True))

    op.add_column("data_domains", sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_data_domains_owner_id", "data_domains", "users", ["owner_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_data_domains_owner_id", "data_domains", ["owner_id"])
    op.execute(
        """
        UPDATE data_domains d SET owner_id = (
            SELECT a.user_id FROM audit_logs a
            WHERE a.action = 'CREATE' AND a.entity_id = d.id::text AND a.user_id IS NOT NULL
            ORDER BY a.created_at LIMIT 1
        )
        """
    )
    op.drop_index("ix_data_domains_name", table_name="data_domains")
    op.create_index("ix_data_domains_name", "data_domains", ["name"])
    op.create_unique_constraint("uq_data_domains_owner_name", "data_domains", ["owner_id", "name"])

    # Permissions: only rows for roles/permissions that already exist are
    # touched (on a fresh database the seed creates them after migrations,
    # from the same mapping in app.core.seed_secure).
    codes = ", ".join(f"'{c}'" for c in USER_PRODUCT_PERMISSIONS)
    op.execute(
        f"""
        INSERT INTO role_permissions (id, role_id, permission_id)
        SELECT gen_random_uuid(), r.id, p.id
        FROM roles r JOIN permissions p ON p.code IN ({codes})
        WHERE r.name = 'User'
          AND NOT EXISTS (
            SELECT 1 FROM role_permissions rp WHERE rp.role_id = r.id AND rp.permission_id = p.id
          )
        """
    )
    op.execute(
        """
        DELETE FROM role_permissions rp
        USING roles r, permissions p
        WHERE rp.role_id = r.id AND rp.permission_id = p.id
          AND r.name = 'Manager' AND p.code = 'audit:view'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        INSERT INTO role_permissions (id, role_id, permission_id)
        SELECT gen_random_uuid(), r.id, p.id FROM roles r JOIN permissions p ON p.code = 'audit:view'
        WHERE r.name = 'Manager'
          AND NOT EXISTS (SELECT 1 FROM role_permissions rp WHERE rp.role_id = r.id AND rp.permission_id = p.id)
        """
    )
    codes = ", ".join(f"'{c}'" for c in USER_PRODUCT_PERMISSIONS)
    op.execute(
        f"""
        DELETE FROM role_permissions rp USING roles r, permissions p
        WHERE rp.role_id = r.id AND rp.permission_id = p.id AND r.name = 'User' AND p.code IN ({codes})
        """
    )
    # Restoring global uniqueness fails if two owners now share a name;
    # rename one of them first.
    op.drop_constraint("uq_data_domains_owner_name", "data_domains", type_="unique")
    op.drop_index("ix_data_domains_name", table_name="data_domains")
    op.create_index("ix_data_domains_name", "data_domains", ["name"], unique=True)
    op.drop_index("ix_data_domains_owner_id", table_name="data_domains")
    op.drop_constraint("fk_data_domains_owner_id", "data_domains", type_="foreignkey")
    op.drop_column("data_domains", "owner_id")
    op.drop_column("quality_check_runs", "quality_score")
