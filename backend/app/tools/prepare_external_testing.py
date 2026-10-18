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

    # also check passwords you keep outside the repository (one per line):
    python -m app.tools.prepare_external_testing --candidates-file /path/to/list
    ... | docker exec -i dq-backend python -m app.tools.prepare_external_testing --candidates-file -

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
from app.core.seed_secure import DEMO_EMAILS
from app.database import async_session_factory
from app.models.data_hierarchy import Dataset
from app.models.token import RefreshToken
from app.models.user import User
from app.utils.audit_logger import create_audit_log


# Test-only passwords that appear in backend/tests (which only ever run
# against an in-memory SQLite database) or that earlier manual test runs used.
# Someone could have typed one into a real instance while trying things out,
# so accounts using them are flagged.
#
# Legacy development credentials (old seed/demo/admin defaults and the old
# default database password) are deliberately not listed here any more; demo
# accounts are recognised by e-mail instead. Pass any other
# password you know is public with --candidates-file (kept outside the repo).
KNOWN_PASSWORDS = [
    "AdminPass123!",
    "TestPass123!",
    "TestPassword123!",
    "ValidPass123!",
    "NewValid456!",
    "Changed789!",
    "Another789!",
    "WrongPass123!",
    "STRONG_PASSWORD",
]


def load_candidates(path: str | None) -> list[str]:
    candidates = list(KNOWN_PASSWORDS)
    if path:
        stream = sys.stdin if path == "-" else open(path, encoding="utf-8")
        with stream:
            candidates += [line.strip() for line in stream if line.strip()]
    return list(dict.fromkeys(candidates))


def matching_known_password(password_hash: str, candidates: list[str]) -> bool:
    for candidate in candidates:
        try:
            if verify_password(candidate, password_hash):
                return True
        except Exception:  # noqa: BLE001 - unknown/legacy hash format
            return False
    return False


async def run(apply: bool, candidates: list[str]) -> int:
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
            if await asyncio.to_thread(matching_known_password, user.password_hash, candidates):
                reasons.append("password is published in the repository")
            if reasons:
                flagged.append((user, reasons))

        print(f"Checked {len(users)} accounts against {len(candidates)} known passwords.\n")
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
    parser.add_argument("--candidates-file", metavar="PATH",
                        help="extra known passwords, one per line ('-' reads stdin); never printed")
    args = parser.parse_args()
    sys.exit(asyncio.run(run(args.apply, load_candidates(args.candidates_file))))


if __name__ == "__main__":
    main()
