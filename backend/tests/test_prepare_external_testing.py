import secrets

from app.core.security import hash_password
from app.core.seed_secure import DEMO_EMAILS
from app.tools import prepare_external_testing as tool
from app.tools.prepare_external_testing import KNOWN_PASSWORDS, load_candidates, matching_known_password


def test_published_passwords_are_detected():
    assert matching_known_password(hash_password(KNOWN_PASSWORDS[0]), KNOWN_PASSWORDS)
    assert matching_known_password(hash_password(KNOWN_PASSWORDS[-1]), KNOWN_PASSWORDS)


def test_private_password_is_not_flagged():
    assert not matching_known_password(hash_password("a-private-passphrase-nobody-published"), KNOWN_PASSWORDS)


def test_unknown_hash_format_is_not_flagged():
    assert not matching_known_password("not-a-real-hash", KNOWN_PASSWORDS)


def test_extra_candidates_file_is_loaded(tmp_path):
    extra = secrets.token_urlsafe(12)  # generated per run, never a fixed value
    path = tmp_path / "known.txt"
    path.write_text(f"\n{extra}\n{KNOWN_PASSWORDS[0]}\n", encoding="utf-8")
    candidates = load_candidates(str(path))
    assert extra in candidates
    assert len(candidates) == len(KNOWN_PASSWORDS) + 1  # duplicates and blank lines dropped
    assert matching_known_password(hash_password(extra), candidates)


def test_demo_accounts_are_recognised_by_email():
    # The tool and the login guard share one definition of the demo accounts.
    assert tool.DEMO_EMAILS == DEMO_EMAILS
