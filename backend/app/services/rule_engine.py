"""
Deterministic execution of user-defined quality rules.

A rule is *executable* when it is tied to a dataset, names a column
(`target_field`) and has one of the rule types below. Any other rule is a
documentation-only definition and the UI says so - it is never shown as if
it had run.

Rule types and what counts as a failing row:

  not_null        the value is missing (empty cell or blank text)
  unique          the (trimmed) value appears in more than one row
  email_format    the value is not a syntactically valid e-mail address
  numeric_range   the value is not a number, or is outside [min, max]
  allowed_values  the value is not one of `values`
  date_range      the value is not an unambiguous date, or is outside
                  [min_date, max_date]

Except for not_null, missing values are not judged (that is not_null's job),
so they are excluded from `records_checked`.
"""
import re
from typing import Any

import pandas as pd

from app.services.data_cleaning_service import _is_missing, _parse_date, _parse_number

EXECUTABLE_RULE_TYPES = {"not_null", "unique", "email_format", "numeric_range", "allowed_values", "date_range"}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_ALLOWED_VALUES = 500


class RuleDefinitionError(ValueError):
    pass


def is_executable(rule_type: str | None, dataset_id: Any, target_field: str | None, definition: dict | None) -> bool:
    if (definition or {}).get("source") == "auto_discovery":
        return False
    return rule_type in EXECUTABLE_RULE_TYPES and dataset_id is not None and bool(target_field)


def validate_definition(rule_type: str, target_field: str | None, definition: dict | None) -> dict:
    """Validate and normalise the parameters of an executable rule type.
    Raises RuleDefinitionError with a readable message."""
    d = dict(definition or {})
    if rule_type not in EXECUTABLE_RULE_TYPES:
        return d
    if not target_field or not str(target_field).strip():
        raise RuleDefinitionError("This rule type needs a column (target_field).")

    if rule_type == "numeric_range":
        lo, hi = d.get("min"), d.get("max")
        for name, v in (("min", lo), ("max", hi)):
            if v is not None and (isinstance(v, bool) or not isinstance(v, (int, float))):
                raise RuleDefinitionError(f"'{name}' must be a number.")
        if lo is None and hi is None:
            raise RuleDefinitionError("numeric_range needs 'min', 'max' or both.")
        if lo is not None and hi is not None and lo > hi:
            raise RuleDefinitionError("'min' must not be greater than 'max'.")
        if d.get("decimal_separator", ".") not in (".", ","):
            raise RuleDefinitionError("'decimal_separator' must be '.' or ','.")

    elif rule_type == "allowed_values":
        values = d.get("values")
        if not isinstance(values, list) or not values or not all(isinstance(v, str) and v.strip() for v in values):
            raise RuleDefinitionError("allowed_values needs a non-empty list of text 'values'.")
        if len(values) > MAX_ALLOWED_VALUES:
            raise RuleDefinitionError(f"At most {MAX_ALLOWED_VALUES} allowed values.")
        d["values"] = [v.strip() for v in values]
        d["case_sensitive"] = bool(d.get("case_sensitive", False))

    elif rule_type == "date_range":
        for name in ("min_date", "max_date"):
            if d.get(name) is not None:
                try:
                    pd.to_datetime(d[name], format="%Y-%m-%d")
                except (ValueError, TypeError):
                    raise RuleDefinitionError(f"'{name}' must be a date in YYYY-MM-DD form.")
        if d.get("min_date") and d.get("max_date") and d["min_date"] > d["max_date"]:
            raise RuleDefinitionError("'min_date' must not be after 'max_date'.")
        if d.get("day_first") not in (None, True, False):
            raise RuleDefinitionError("'day_first' must be true, false or omitted.")

    elif rule_type == "unique":
        d["case_sensitive"] = bool(d.get("case_sensitive", True))

    return d


def evaluate_rule(df: pd.DataFrame, rule_type: str, column: str, definition: dict | None) -> dict:
    """Run one rule over a dataframe. Never raises for data problems:
    returns status "error" when the rule cannot be evaluated (e.g. the
    column no longer exists)."""
    d = definition or {}
    if column not in df.columns:
        return {"status": "error", "error": f"Column '{column}' does not exist in this version.",
                "records_checked": 0, "records_failed": 0, "bad_rows": [], "reasons": {}}

    series = df[column]
    missing = series.map(_is_missing).astype(bool)
    reasons: dict[str, int] = {}

    def fail(reason: str):
        reasons[reason] = reasons.get(reason, 0) + 1
        return True

    if rule_type == "not_null":
        checked = series
        bad = missing
        if bad.any():
            reasons["missing"] = int(bad.sum())
    else:
        checked = series[~missing]
        if rule_type == "unique":
            key = checked.map(lambda v: str(v).strip() if d.get("case_sensitive", True) else str(v).strip().lower())
            bad = key.duplicated(keep=False)
            if bad.any():
                reasons["duplicate value"] = int(bad.sum())
        elif rule_type == "email_format":
            bad = checked.map(lambda v: not EMAIL_RE.match(str(v).strip()) and fail("invalid e-mail")).astype(bool)
        elif rule_type == "numeric_range":
            lo, hi, sep = d.get("min"), d.get("max"), d.get("decimal_separator", ".")

            def check(v):
                number = _parse_number(str(v), sep)
                if number is None:
                    return fail("not a number")
                if (lo is not None and number < lo) or (hi is not None and number > hi):
                    return fail("out of range")
                return False
            bad = checked.map(check).astype(bool)
        elif rule_type == "allowed_values":
            sensitive = d.get("case_sensitive", False)
            allowed = {v if sensitive else v.lower() for v in d.get("values", [])}
            bad = checked.map(lambda v: ((str(v).strip() if sensitive else str(v).strip().lower()) not in allowed) and fail("not an allowed value")).astype(bool)
        elif rule_type == "date_range":
            lo = pd.to_datetime(d["min_date"]) if d.get("min_date") else None
            hi = pd.to_datetime(d["max_date"]) if d.get("max_date") else None

            def check(v):
                parsed, why = _parse_date(str(v), d.get("source_format"), d.get("day_first"))
                if parsed is None:
                    return fail("ambiguous date" if why == "ambiguous" else "not a date")
                if (lo is not None and parsed < lo) or (hi is not None and parsed > hi):
                    return fail("out of range")
                return False
            bad = checked.map(check).astype(bool)
        else:
            return {"status": "error", "error": f"Rule type '{rule_type}' cannot be executed.",
                    "records_checked": 0, "records_failed": 0, "bad_rows": [], "reasons": {}}

    bad_labels = list(checked.index[bad.values]) if len(checked) else []
    return {
        "status": "failed" if bad_labels else "passed",
        "error": None,
        "records_checked": int(len(checked)),
        "records_failed": len(bad_labels),
        "bad_rows": bad_labels,          # dataframe row labels (0-based)
        "reasons": reasons,
    }


def result_details(evaluation: dict) -> str:
    """What is stored with a result: counts per reason and the first failing
    row numbers - never the cell values themselves."""
    import json
    return json.dumps({
        "error": evaluation.get("error"),
        "reasons": evaluation.get("reasons", {}),
        "failing_rows": [int(r) + 1 for r in evaluation.get("bad_rows", [])[:20]],
    })
