"""Unique role links and a default role for role-less accounts

1. user_roles and role_permissions had no uniqueness on their (user, role) /
   (role, permission) pairs, so the same link could be stored twice.
2. Self-registered accounts used to receive no role until email
   verification - which can't happen without SMTP - leaving them able to log
   in but forbidden from every page. Registration now assigns the "User"
   role; this backfills it, once, for existing non-super-admin accounts that
   have no role at all. It runs as a migration rather than at every startup
   so that an admin who later removes all of a user's roles on purpose is
   not overridden on the next restart.

Revision ID: 011
Revises: 010
Create Date: 2026-10-16 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint("uq_user_roles_user_role", "user_roles", ["user_id", "role_id"])
    op.create_unique_constraint("uq_role_permissions_role_permission", "role_permissions", ["role_id", "permission_id"])

    # gen_random_uuid() is built into PostgreSQL 13+. On a fresh database the
    # "User" role doesn't exist yet (the seed creates it after migrations), so
    # this inserts nothing - which is correct, as there are no accounts either.
    op.execute(
        """
        INSERT INTO user_roles (id, user_id, role_id)
        SELECT gen_random_uuid(), u.id, r.id
        FROM users u
        CROSS JOIN roles r
        WHERE r.name = 'User'
          AND u.is_super_admin = false
          AND NOT EXISTS (SELECT 1 FROM user_roles ur WHERE ur.user_id = u.id)
        """
    )


def downgrade() -> None:
    # The backfilled role links are deliberately kept: removing them would
    # lock those users out again, and they can't be told apart from links an
    # admin made afterwards.
    op.drop_constraint("uq_role_permissions_role_permission", "role_permissions", type_="unique")
    op.drop_constraint("uq_user_roles_user_role", "user_roles", type_="unique")
