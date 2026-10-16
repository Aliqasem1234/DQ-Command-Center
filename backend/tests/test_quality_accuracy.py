"""Profiling and quality-score results checked against hand-computed values.

The file below was analysed by hand (see the comments); the services must
reproduce those numbers exactly.
"""
import pytest

from app.config import settings
from app.services.dataframe_io import read_dataframe
from app.services.profiling_service import profile_column
from app.services.quality_discovery_service import _detect_checks, compute_quality_score

CSV = (
    "customer_id,name,email,signup_date,amount,city\n"
    "1,Anna,anna@example.com,2024-01-05,10.50,Stockholm\n"   # row 1: city inconsistent (with row 2)
    "2,Bo,bo@example,2024-02-30,abc,stockholm\n"             # row 2: bad email, bad date, bad amount, city
    "3,Cecilia,,2024-03-01,7.25,Malmö\n"                     # row 3: email missing, id repeated
    "3,Cecilia,,2024-03-01,7.25,Malmö\n"                     # row 4: exact duplicate of row 3 (all 6 cells)
    "5,  ,dan@example.com,not a date,12.00, Göteborg\n"      # row 5: name blank, bad date
    "6,Eva,eva@example.com,2024-04-10,,Göteborg\n"           # row 6: amount missing
    "7,Fia,fia@example.com,2024-05-11,3.10,Uppsala\n"
    "8,Gus,gus@example.com,2024-06-12,4.20,Uppsala\n"
    "9,Hal,hal@example.com,2024-07-13,5.30,Lund\n"
    "10,Ida,ida@example.com,2024-08-14,6.40,Lund\n"
)


@pytest.fixture
def df(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    (tmp_path / "accuracy.csv").write_text(CSV, encoding="utf-8")
    return read_dataframe("accuracy.csv", "csv")


def test_profile_matches_hand_computed_values(df):
    profiles = {c: profile_column(df[c]) for c in df.columns}
    assert {c: p["null_count"] for c, p in profiles.items()} == {
        "customer_id": 0, "name": 1, "email": 2, "signup_date": 0, "amount": 1, "city": 0,
    }
    assert {c: p["inferred_type"] for c, p in profiles.items() if c != "name"} == {
        "customer_id": "integer", "email": "email", "signup_date": "datetime", "amount": "float", "city": "string",
    }
    amount = profiles["amount"]
    # 10.50 + 7.25 + 7.25 + 12.00 + 3.10 + 4.20 + 5.30 + 6.40 = 56.00 over 8 valid values ("abc" excluded)
    assert float(amount["min_value"]) == 3.1
    assert float(amount["max_value"]) == 12.0
    assert amount["average_value"] == pytest.approx(7.0)
    assert profiles["customer_id"]["duplicate_count"] == 1


def test_scan_findings_and_score_match_hand_computed_values(df):
    findings = {f["check_key"]: f for f in _detect_checks(df, {}) if f["bad_count"] > 0}
    assert {k: f["bad_count"] for k, f in findings.items()} == {
        "duplicate_rows": 1,
        "completeness:name": 1,
        "completeness:email": 2,
        "validity_email:email": 1,
        "validity_date:signup_date": 2,
        "completeness:amount": 1,
        "validity_numeric:amount": 1,
        "uniqueness:customer_id": 1,
        "consistency:city": 2,
    }
    # Union of bad cells: row 4 entirely (6) + (3,id) (5,name) (2,email)
    # (3,email) (2,date) (5,date) (2,amount) (6,amount) (1,city) (2,city) = 16
    # of 60 cells -> 100 - 16/60*100 = 73.33...
    assert compute_quality_score(df, list(findings.values())) == pytest.approx(100 - 16 / 60 * 100)


def test_clean_file_scores_100(df):
    clean = df.iloc[6:].reset_index(drop=True)  # rows 7-10 have no problems
    findings = [f for f in _detect_checks(clean, {}) if f["bad_count"] > 0]
    assert findings == []
    assert compute_quality_score(clean, findings) == 100.0
