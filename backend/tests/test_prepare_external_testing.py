from app.core.security import hash_password
from app.tools.prepare_external_testing import KNOWN_PASSWORDS, matching_known_password


def test_published_passwords_are_detected():
    assert matching_known_password(hash_password("[REDACTED-DEV-CREDENTIAL]"))
    assert matching_known_password(hash_password(KNOWN_PASSWORDS[-1]))


def test_private_password_is_not_flagged():
    assert not matching_known_password(hash_password("a-private-passphrase-nobody-published"))


def test_unknown_hash_format_is_not_flagged():
    assert not matching_known_password("not-a-real-hash")
