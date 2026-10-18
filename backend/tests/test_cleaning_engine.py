"""Deterministic cleaning operations: known input -> known output."""
import numpy as np
import pandas as pd
import pytest

from app.services.data_cleaning_service import (
    CleaningOperationError, apply_operations, diff_sample, potential_duplicate_count,
)


def frame(**cols):
    return pd.DataFrame(cols, dtype=object)


def run(df, *ops):
    return apply_operations(df, list(ops))


def test_trim_collapse_and_control_characters_keep_missing_values():
    df = frame(a=["  x  ", "a   b", np.nan, "c​d\te\x00f"])
    out, s = run(df, {"type": "trim_whitespace"}, {"type": "collapse_whitespace"}, {"type": "remove_control_characters"})
    assert out["a"].tolist()[:2] == ["x", "a b"]
    assert pd.isna(out["a"][2])                      # NaN never becomes "nan"
    assert out["a"][3] == "cd ef"                     # zero-width + NUL removed, tab -> space
    assert s["values_changed"] == 3 and s["rows_removed"] == 0


def test_standardize_case_rejects_unknown_case():
    out, _ = run(frame(a=["anna", "BO"]), {"type": "standardize_case", "case": "title"})
    assert out["a"].tolist() == ["Anna", "Bo"]
    with pytest.raises(CleaningOperationError):
        run(frame(a=["x"]), {"type": "standardize_case", "case": "camel"})


class TestDates:
    OP = {"type": "normalize_dates", "columns": ["d"]}

    def test_unambiguous_values_are_converted(self):
        out, s = run(frame(d=["2024-03-05", "31/12/2024", "12/31/2024", "5 Mar 2024", np.nan]), self.OP)
        assert out["d"].tolist()[:4] == ["2024-03-05", "2024-12-31", "2024-12-31", "2024-03-05"]
        assert pd.isna(out["d"][4])
        assert s["operations_report"][0]["skipped"] == 0

    def test_ambiguous_day_month_is_not_guessed(self):
        out, s = run(frame(d=["01/02/2024", "not a date"]), self.OP)
        assert out["d"].tolist() == ["01/02/2024", "not a date"]   # unchanged
        reasons = [e["reason"] for e in s["operations_report"][0]["skipped_examples"]]
        assert reasons == ["ambiguous", "invalid"]

    def test_explicit_day_first_and_source_format(self):
        out, _ = run(frame(d=["01/02/2024"]), {**self.OP, "day_first": True})
        assert out["d"][0] == "2024-02-01"
        out, _ = run(frame(d=["01/02/2024"]), {**self.OP, "day_first": False})
        assert out["d"][0] == "2024-01-02"
        out, s = run(frame(d=["05.03.2024", "2024-03-05"]), {**self.OP, "source_format": "%d.%m.%Y"})
        assert out["d"].tolist() == ["2024-03-05", "2024-03-05"]
        assert s["operations_report"][0]["skipped"] == 1  # second value doesn't match the explicit format... and is kept

    def test_columns_are_required(self):
        with pytest.raises(CleaningOperationError, match="explicit columns"):
            run(frame(d=["2024-01-01"]), {"type": "normalize_dates"})


class TestConvertType:
    def test_integer(self):
        df = frame(n=["42", " 7 ", "12.0", "12.5", "abc", np.nan])
        out, s = run(df, {"type": "convert_type", "columns": ["n"], "target": "integer"})
        assert out["n"].tolist()[:5] == ["42", "7", "12", "12.5", "abc"]   # invalid kept as-is
        assert s["operations_report"][0]["skipped"] == 2
        out, _ = run(df, {"type": "convert_type", "columns": ["n"], "target": "integer", "on_invalid": "set_missing"})
        assert pd.isna(out["n"][3]) and pd.isna(out["n"][4])

    def test_decimal_separators_are_explicit(self):
        out, s = run(frame(n=["1.234,5", "3,25", "1,234"]), {"type": "convert_type", "columns": ["n"], "target": "decimal", "decimal_separator": ","})
        assert out["n"].tolist() == ["1234.5", "3.25", "1.234"]
        out, s = run(frame(n=["1,234", "2.5"]), {"type": "convert_type", "columns": ["n"], "target": "decimal"})
        assert out["n"].tolist() == ["1,234", "2.5"] and s["operations_report"][0]["skipped"] == 1

    def test_boolean(self):
        out, _ = run(frame(b=["Ja", "nej", "TRUE", "0", "kanske"]), {"type": "convert_type", "columns": ["b"], "target": "boolean"})
        assert out["b"].tolist() == ["true", "false", "true", "false", "kanske"]

    def test_invalid_parameters(self):
        for bad in ({"target": "money"}, {"target": "integer", "on_invalid": "drop"}, {"target": "decimal", "decimal_separator": ";"}):
            with pytest.raises(CleaningOperationError):
                run(frame(n=["1"]), {"type": "convert_type", "columns": ["n"], **bad})


def test_map_values_standardizes_categories():
    df = frame(c=[" sthlm", "Stockholm", "GBG", "Malmö", np.nan])
    out, s = run(df, {"type": "map_values", "columns": ["c"], "mapping": {"sthlm": "Stockholm", "gbg": "Göteborg"}})
    assert out["c"].tolist()[:4] == ["Stockholm", "Stockholm", "Göteborg", "Malmö"]   # unmapped unchanged
    assert s["values_changed"] == 2
    with pytest.raises(CleaningOperationError, match="collide"):
        run(df, {"type": "map_values", "columns": ["c"], "mapping": {"A": "x", "a": "y"}})


class TestDuplicates:
    def test_exact_duplicates_and_aligned_diff(self):
        df = frame(id=["1", "2", "2", "3", "4"], v=["a", "b", "b", "c", "d"])
        out, s = run(df, {"type": "remove_duplicate_rows"})
        assert out["id"].tolist() == ["1", "2", "3", "4"]
        # Rows after the removed one are NOT reported as changed (positional
        # comparison used to count 2 changed rows and 4 changed values here).
        assert (s["rows_removed"], s["rows_modified"], s["values_changed"]) == (1, 0, 0)
        assert s["exact_duplicates_before"] == 1 and s["exact_duplicates_after"] == 0
        samples = diff_sample(s)
        assert samples == [{"row": 3, "before": {"id": "2", "v": "b"}, "after": None}]

    def test_subset_columns_and_keep_last(self):
        df = frame(email=["a@x.se", "a@x.se", "b@x.se"], name=["Anna", "Anna B", "Bo"])
        out, s = run(df, {"type": "remove_duplicate_rows", "columns": ["email"], "keep": "last"})
        assert out["name"].tolist() == ["Anna B", "Bo"]
        assert "email" in s["operations_report"][0]["note"]

    def test_similar_rows_are_reported_not_removed(self):
        df = frame(n=["Anna ", "anna", "Bo"])
        out, s = run(df, {"type": "remove_duplicate_rows"})
        assert len(out) == 3                         # not merged
        assert s["potential_duplicates_after"] == 1  # but flagged
        assert potential_duplicate_count(frame(n=["x", "x"])) == 0  # exact duplicates are not "potential"


class TestFillMissing:
    def test_fill_value_requires_a_value(self):
        with pytest.raises(CleaningOperationError):
            run(frame(a=[np.nan]), {"type": "fill_missing", "columns": ["a"], "strategy": "fill_value"})
        out, _ = run(frame(a=[np.nan, " ", "x"]), {"type": "fill_missing", "columns": ["a"], "strategy": "fill_value", "value": "okänd"})
        assert out["a"].tolist() == ["okänd", "okänd", "x"]

    def test_mean_median_need_numbers_and_report_exclusions(self):
        out, s = run(frame(a=["1", "2", np.nan, "x"]), {"type": "fill_missing", "columns": ["a"], "strategy": "fill_mean"})
        assert out["a"][2] == "1.5" and s["operations_report"][0]["skipped"] == 1
        with pytest.raises(CleaningOperationError, match="no numeric"):
            run(frame(a=["x", np.nan]), {"type": "fill_missing", "columns": ["a"], "strategy": "fill_median"})

    def test_mode_refuses_ties(self):
        with pytest.raises(CleaningOperationError, match="equally common"):
            run(frame(a=["x", "y", np.nan]), {"type": "fill_missing", "columns": ["a"], "strategy": "fill_mode"})

    def test_drop_row(self):
        out, s = run(frame(a=["1", np.nan, "3"], b=["x", "y", "z"]), {"type": "fill_missing", "columns": ["a"], "strategy": "drop_row"})
        assert out["b"].tolist() == ["x", "z"] and s["rows_removed"] == 1 and s["removes_rows"]


def test_request_validation():
    with pytest.raises(CleaningOperationError):
        run(frame(a=["x"]))
    with pytest.raises(CleaningOperationError):
        run(frame(a=["x"]), {"type": "drop_table"})
    with pytest.raises(CleaningOperationError):
        run(frame(a=["x"]), "trim")
    with pytest.raises(CleaningOperationError, match="Unknown column"):
        run(frame(a=["x"]), {"type": "trim_whitespace", "columns": ["nope"]})
    with pytest.raises(CleaningOperationError, match="50"):
        run(frame(a=["x"]), *([{"type": "trim_whitespace"}] * 51))


def test_changed_rows_are_paired_by_identity_after_removals():
    df = frame(id=["1", "1", "2"], name=[" a", " a", " b"])
    _, s = run(df, {"type": "remove_duplicate_rows"}, {"type": "trim_whitespace"})
    samples = diff_sample(s)
    changed = [x for x in samples if x["after"]]
    assert [(x["row"], x["before"]["name"], x["after"]["name"]) for x in changed] == [(1, " a", "a"), (3, " b", "b")]
