"""
Find - and optionally disable - accounts that outsiders could sign in to
because their password is publicly known.

An account is flagged when either:
  * it is one of the demo users the development seed creates, or
  * its password hash verifies against a password that appears in this
    repository (tests, docs, old seed code, example env files), whatever
    the account's email is.

Usage (inside the backend container):

    python -m app.tools.prepare_external_testing            # dry run: report only
    python -m app.tools.prepare_external_testing --apply    # deactivate flagged accounts

--apply only *deactivates* (is_active = false) non-super-admin accounts and
revokes their sessions; nothing is deleted, so it is reversible from the
Users page (or by setting is_active back to true). Each change is written to
the audit log. Super admins are never changed automatically: if one matches
a known password the tool reports it and exits non-zero so the password gets
changed by a person.

Passwords and hashes are never printed.
"""
import argparse
import asyncio
import sys
from datetime import datetime, timezone

from sqlalchemy import func, select, update

from app.core.security import verify_password
from app.database import async_session_factory
from app.models.data_hierarchy import Dataset
from app.models.token import RefreshToken
from app.models.user import User
from app.utils.audit_logger import create_audit_log

DEMO_EMAILS = {f"demo{i}@dqcommandcenter.io" for i in (1, 2, 3)}

# Every password literal found in the repository, its docs or its git
# history. Extend this list if new ones are added anywhere public.
KNOWN_PASSWORDS = [
    "[REDACTED-DEV-CREDENTIAL]",
    "[REDACTED-DEV-CREDENTIAL]",
    "AdminPass123!",
    "TestPass123!",
    "TestPassword123!",
    "[REDACTED-DEV-CREDENTIAL]",
    "[REDACTED-DEV-CREDENTIAL]",
    "ValidPass123!",
    "NewValid456!",
    "Changed789!",
    "Another789!",
    "WrongPass123!",
    "STRONG_PASSWORD",
    "[REDACTED-DEV-CREDENTIAL]",
    "[REDACTED-DEV-CREDENTIAL]",
]


def matching_known_password(password_hash: str) -> bool:
    for candidate in KNOWN_PASSWORDS:
        try:
            if verify_password(candidate, password_hash):
                return True
        except Exception:  # noqa: BLE001 - unknown/legacy hash format
            return False
    return False


async def run(apply: bool) -> int:
    async with async_session_factory() as db:
        users = (await db.execute(select(User).order_by(User.created_at))).scalars().all()
        owned = dict(
            (await db.execute(select(Dataset.data_owner_id, func.count()).group_by(Dataset.data_owner_id))).all()
        )

        flagged = []
        for user in users:
            reasons = []
            if user.email.lower() in DEMO_EMAILS:
                reasons.append("seeded demo account")
            # Argon2 verification is deliberately slow; run it off the loop.
            if await asyncio.to_thread(matching_known_password, user.password_hash):
                reasons.append("password is published in the repository")
            if reasons:
                flagged.append((user, reasons))

        print(f"Checked {len(users)} accounts against {len(KNOWN_PASSWORDS)} known passwords.\n")
        if not flagged:
            print("No known-credential accounts found.")
            return 0

        blocked_super_admins = []
        print(f"{'email':45} {'active':6} {'super':5} {'datasets':8} {'last login':20} reason")
        for user, reasons in flagged:
            last = user.last_login_at.strftime("%Y-%m-%d %H:%M") if user.last_login_at else "never"
            print(f"{user.email:45} {str(user.is_active):6} {str(user.is_super_admin):5} "
                  f"{owned.get(user.id, 0):<8} {last:20} {'; '.join(reasons)}")
            if user.is_super_admin and user.is_active:
                blocked_super_admins.append(user)

        if not apply:
            print("\nDry run - nothing changed. Re-run with --apply to deactivate the non-super-admin accounts above.")
        else:
            now = datetime.now(timezone.utc)
            changed = 0
            for user, reasons in flagged:
                if user.is_super_admin or not user.is_active:
                    continue
                user.is_active = False
                user.updated_at = now
                await db.execute(
                    update(RefreshToken)
                    .where(RefreshToken.user_id == user.id, RefreshToken.is_revoked == False)  # noqa: E712
                    .values(is_revoked=True)
                )
                await create_audit_log(
                    db, None, "DEACTIVATE", "user", str(user.id), entity_name=user.email,
                    old_values={"is_active": True},
                    new_values={"is_active": False, "reason": "known credentials before external testing: " + "; ".join(reasons)},
                )
                changed += 1
            await db.commit()
            print(f"\nDeactivated {changed} account(s) and revoked their sessions. Their data is untouched.")

        if blocked_super_admins:
            print("\nACTION REQUIRED: these super admin accounts use a published password and were NOT changed.")
            print("Sign in as each and change the password (Settings -> Change password) before external testing:")
            for user in blocked_super_admins:
                print(f"  - {user.email}")
            return 2
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="deactivate flagged accounts (default: report only)")
    args = parser.parse_args()
    sys.exit(asyncio.run(run(args.apply)))


if __name__ == "__main__":
    main()
