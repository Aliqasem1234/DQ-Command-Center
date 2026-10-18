"""Executable quality rules: known input -> known result."""
import json

import numpy as np
import pandas as pd
import pytest

from app.services.rule_engine import RuleDefinitionError, evaluate_rule, is_executable, result_details, validate_definition

DF = pd.DataFrame({
    "id": ["1", "2", "2", "4", np.nan],
    "email": ["a@x.se", "bad", np.nan, "c@y.com", "d@z.org"],
    "age": ["30", "-1", "abc", "120", np.nan],
    "city": ["Stockholm", "stockholm", "Oslo", np.nan, "Malmö"],
    "born": ["2000-01-01", "01/02/2000", "31/12/1899", "x", np.nan],
}, dtype=object)


def ev(rule_type, column, **definition):
    return evaluate_rule(DF, rule_type, column, definition)


def test_not_null_counts_missing():
    r = ev("not_null", "id")
    assert (r["status"], r["records_checked"], r["records_failed"], r["bad_rows"]) == ("failed", 5, 1, [4])


def test_unique_flags_every_repeated_row_and_ignores_missing():
    r = ev("unique", "id")
    assert r["bad_rows"] == [1, 2] and r["records_checked"] == 4
    assert ev("unique", "city", case_sensitive=False)["bad_rows"] == [0, 1]
    assert ev("unique", "city")["status"] == "passed"


def test_email_format():
    r = ev("email_format", "email")
    assert r["bad_rows"] == [1] and r["records_checked"] == 4 and r["reasons"] == {"invalid e-mail": 1}


def test_numeric_range():
    r = ev("numeric_range", "age", min=0, max=110)
    assert r["bad_rows"] == [1, 2, 3]
    assert r["reasons"] == {"out of range": 2, "not a number": 1}


def test_allowed_values_case_insensitive_by_default():
    assert ev("allowed_values", "city", values=["Stockholm", "Malmö"])["bad_rows"] == [2]
    assert ev("allowed_values", "city", values=["Stockholm", "Malmö"], case_sensitive=True)["bad_rows"] == [1, 2]


def test_date_range_never_guesses_ambiguous_dates():
    r = ev("date_range", "born", min_date="1900-01-01")
    assert r["bad_rows"] == [1, 2, 3]
    assert r["reasons"] == {"ambiguous date": 1, "out of range": 1, "not a date": 1}
    r = ev("date_range", "born", min_date="1900-01-01", day_first=True)
    assert r["bad_rows"] == [2, 3]


def test_missing_column_is_an_error_not_a_crash():
    r = ev("not_null", "gone")
    assert r["status"] == "error" and "does not exist" in r["error"]


def test_result_details_store_row_numbers_not_values():
    details = json.loads(result_details(ev("email_format", "email")))
    assert details["failing_rows"] == [2]
    assert "bad" not in json.dumps(details)      # the offending cell value is not stored


@pytest.mark.parametrize("rule_type,field,definition", [
    ("numeric_range", "age", {}),
    ("numeric_range", "age", {"min": 5, "max": 1}),
    ("numeric_range", "age", {"min": "5"}),
    ("allowed_values", "city", {"values": []}),
    ("allowed_values", "city", {"values": ["ok", ""]}),
    ("date_range", "born", {"min_date": "01/01/2000"}),
    ("date_range", "born", {"min_date": "2001-01-01", "max_date": "2000-01-01"}),
    ("not_null", "", {}),
])
def test_invalid_definitions_are_rejected(rule_type, field, definition):
    with pytest.raises(RuleDefinitionError):
        validate_definition(rule_type, field, definition)


def test_executable_requires_type_dataset_and_column():
    assert is_executable("not_null", "ds", "id", {})
    assert not is_executable("not_null", None, "id", {})
    assert not is_executable("required_field", "ds", "id", {})          # free-text type: documentation only
    assert not is_executable("not_null", "ds", "id", {"source": "auto_discovery"})
