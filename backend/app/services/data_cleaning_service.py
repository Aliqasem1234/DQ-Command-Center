"""
Deterministic data cleaning operations.

Every operation is applied to an in-memory copy of the dataframe; the
source file is never touched. The SAME function (`apply_operations`) is
used for the preview and for the real run, so a preview can never show a
different result from what is saved.

Design rules (see docs/DATA_CLEANING_GUIDE.md):
  * Operations keep the original row labels (index) until the very end, so
    the diff aligns rows by identity - removing a row does not make every
    following row look "changed".
  * Nothing ambiguous is guessed: a value that can't be converted or parsed
    unambiguously is left unchanged (or, when explicitly requested, set to
    missing) and is reported as skipped/invalid.
  * Missing values (NaN or blank text) are never turned into text such as
    "nan" and are left alone unless the operation is about missing values.

All data arriving here was loaded with dtype=str (see dataframe_io), so
values are strings or NaN.
"""
import re
import unicodedata
from typing import Any

import pandas as pd

VALID_OPERATION_TYPES = {
    "trim_whitespace",
    "collapse_whitespace",
    "remove_control_characters",
    "standardize_case",
    "normalize_dates",
    "convert_type",
    "map_values",
    "remove_duplicate_rows",
    "fill_missing",
}

# Operations that can remove rows; the UI asks for confirmation before
# applying a run that contains one of them.
ROW_REMOVING_OPERATIONS = {"remove_duplicate_rows"}

# C0/C1 control characters plus invisible "format" characters that commonly
# sneak in from copy/paste (zero-width space/joiners, BOM).
_INVISIBLE = {"​", "‌", "‍", "⁠", "﻿"}

_TRUE = {"true", "yes", "y", "1", "ja", "sant"}
_FALSE = {"false", "no", "n", "0", "nej", "falskt"}

# Formats tried (in order) when no explicit source format is given. Only
# formats whose meaning is unambiguous are listed; day/month order for
# "01/02/2024"-style values is never guessed (see _parse_date).
_UNAMBIGUOUS_DATE_FORMATS = ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d", "%Y%m%d", "%d %b %Y", "%d %B %Y", "%b %d %Y", "%B %d %Y"]
_SLASHED = re.compile(r"^\s*(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})\s*$")


class CleaningOperationError(ValueError):
    pass


def _is_missing(value: Any) -> bool:
    return value is None or (isinstance(value, float) and pd.isna(value)) or (isinstance(value, str) and value.strip() == "") or (value is pd.NA)


def _target_columns(df: pd.DataFrame, op: dict) -> list[str]:
    columns = op.get("columns") or ([op["column"]] if op.get("column") else None)
    if columns is None or columns == "all":
        return list(df.columns)
    if isinstance(columns, str):
        columns = [columns]
    if not isinstance(columns, list) or not all(isinstance(c, str) for c in columns):
        raise CleaningOperationError("'columns' must be a list of column names or \"all\".")
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise CleaningOperationError(f"Unknown column(s): {', '.join(missing)}")
    return columns


def _require_columns(df: pd.DataFrame, op: dict, name: str) -> list[str]:
    """For operations that must not silently run on every column."""
    if not (op.get("columns") or op.get("column")) or op.get("columns") == "all":
        raise CleaningOperationError(f"'{name}' needs explicit columns.")
    return _target_columns(df, op)


def _map_text(series: pd.Series, fn) -> pd.Series:
    return series.map(lambda v: fn(v) if isinstance(v, str) else v)


def _strip_control(value: str) -> str:
    out = []
    for ch in value:
        if ch in ("\t", "\n", "\r"):
            out.append(" ")
        elif ch in _INVISIBLE or unicodedata.category(ch) == "Cc":
            continue
        else:
            out.append(ch)
    return "".join(out)


def _parse_number(value: str, decimal_separator: str) -> float | None:
    text = value.strip().replace(" ", "").replace(" ", "")
    if decimal_separator == ",":
        if text.count(",") > 1:
            return None
        text = text.replace(".", "").replace(",", ".")  # 1.234,5 -> 1234.5
    elif "," in text:
        return None  # a comma with "." as decimal separator is ambiguous (1,234?)
    try:
        number = float(text)
    except ValueError:
        return None
    return number if pd.notna(number) and number not in (float("inf"), float("-inf")) else None


def _format_number(number: float, target: str) -> str | None:
    if target == "integer":
        if not float(number).is_integer():
            return None  # 12.5 is not an integer; never round silently
        return str(int(number))
    text = repr(round(number, 10))
    return text[:-2] if text.endswith(".0") else text


def _parse_date(value: str, source_format: str | None, day_first: bool | None):
    """Return (datetime | None, reason). reason is 'ambiguous' or 'invalid'
    when parsing is refused."""
    text = value.strip()
    if source_format:
        try:
            return pd.to_datetime(text, format=source_format), None
        except (ValueError, TypeError):
            return None, "invalid"
    for fmt in _UNAMBIGUOUS_DATE_FORMATS:
        try:
            return pd.to_datetime(text, format=fmt), None
        except (ValueError, TypeError):
            continue
    match = _SLASHED.match(text)
    if match:
        a, b = int(match.group(1)), int(match.group(2))
        if a > 12 and b <= 12:
            order = "day_first"
        elif b > 12 and a <= 12:
            order = "month_first"
        elif day_first is None:
            return None, "ambiguous"  # e.g. 01/02/2024: January or February?
        else:
            order = "day_first" if day_first else "month_first"
        year = match.group(3)
        fmt = ("%d/%m/" if order == "day_first" else "%m/%d/") + ("%Y" if len(year) == 4 else "%y")
        normalized = re.sub(r"[.\-]", "/", text)
        try:
            return pd.to_datetime(normalized, format=fmt), None
        except (ValueError, TypeError):
            return None, "invalid"
    return None, "invalid"


def _apply_one(df: pd.DataFrame, op: dict) -> tuple[pd.DataFrame, dict]:
    """Apply one operation. Returns the new dataframe (index labels kept)
    and a report: {"skipped": n, "skipped_examples": [...], "note": str}."""
    if not isinstance(op, dict):
        raise CleaningOperationError("Each operation must be an object.")
    op_type = op.get("type")
    if op_type not in VALID_OPERATION_TYPES:
        raise CleaningOperationError(f"Unknown operation type: {op_type}")

    df = df.copy()
    report: dict = {"skipped": 0, "skipped_examples": []}

    def skip(column: str, value: Any, reason: str):
        report["skipped"] += 1
        if len(report["skipped_examples"]) < 5:
            report["skipped_examples"].append({"column": column, "value": str(value), "reason": reason})

    if op_type == "trim_whitespace":
        for col in _target_columns(df, op):
            df[col] = _map_text(df[col], str.strip)

    elif op_type == "collapse_whitespace":
        for col in _target_columns(df, op):
            df[col] = _map_text(df[col], lambda v: " ".join(v.split()))

    elif op_type == "remove_control_characters":
        for col in _target_columns(df, op):
            df[col] = _map_text(df[col], _strip_control)

    elif op_type == "standardize_case":
        case = op.get("case", "lower")
        funcs = {"lower": str.lower, "upper": str.upper, "title": str.title}
        if case not in funcs:
            raise CleaningOperationError(f"Invalid case '{case}' - expected lower/upper/title")
        for col in _target_columns(df, op):
            df[col] = _map_text(df[col], funcs[case])

    elif op_type == "normalize_dates":
        target_format = op.get("target_format", "%Y-%m-%d")
        source_format = op.get("source_format") or None
        day_first = op.get("day_first")
        if day_first not in (None, True, False):
            raise CleaningOperationError("'day_first' must be true, false or omitted.")
        try:
            pd.Timestamp("2000-01-31").strftime(target_format)
        except (ValueError, TypeError):
            raise CleaningOperationError(f"Invalid target date format: {target_format}")
        for col in _require_columns(df, op, "normalize_dates"):
            def convert(v, col=col):
                if _is_missing(v):
                    return v
                parsed, reason = _parse_date(str(v), source_format, day_first)
                if parsed is None:
                    skip(col, v, reason)
                    return v  # left unchanged, never guessed
                return parsed.strftime(target_format)
            df[col] = df[col].map(convert)

    elif op_type == "convert_type":
        target = op.get("target")
        if target not in ("integer", "decimal", "boolean"):
            raise CleaningOperationError("'target' must be integer, decimal or boolean.")
        on_invalid = op.get("on_invalid", "keep")
        if on_invalid not in ("keep", "set_missing"):
            raise CleaningOperationError("'on_invalid' must be keep or set_missing.")
        decimal_separator = op.get("decimal_separator", ".")
        if decimal_separator not in (".", ","):
            raise CleaningOperationError("'decimal_separator' must be '.' or ','.")
        for col in _require_columns(df, op, "convert_type"):
            def convert(v, col=col):
                if _is_missing(v):
                    return v
                text = str(v)
                if target == "boolean":
                    low = text.strip().lower()
                    if low in _TRUE:
                        return "true"
                    if low in _FALSE:
                        return "false"
                    result = None
                else:
                    number = _parse_number(text, decimal_separator)
                    result = _format_number(number, target) if number is not None else None
                if result is None:
                    skip(col, v, "invalid")
                    return pd.NA if on_invalid == "set_missing" else v
                return result
            df[col] = df[col].map(convert)

    elif op_type == "map_values":
        mapping = op.get("mapping")
        if not isinstance(mapping, dict) or not mapping:
            raise CleaningOperationError("'mapping' must be a non-empty object of {from: to}.")
        if not all(isinstance(k, str) and isinstance(v, str) for k, v in mapping.items()):
            raise CleaningOperationError("'mapping' keys and values must be text.")
        case_sensitive = bool(op.get("case_sensitive", False))
        lookup = {(k.strip() if case_sensitive else k.strip().lower()): v for k, v in mapping.items()}
        if len(lookup) != len(mapping):
            raise CleaningOperationError("'mapping' has keys that collide after trimming/case folding.")
        for col in _require_columns(df, op, "map_values"):
            def convert(v):
                if not isinstance(v, str):
                    return v
                key = v.strip() if case_sensitive else v.strip().lower()
                return lookup.get(key, v)  # unmapped values are left as they are
            df[col] = df[col].map(convert)

    elif op_type == "remove_duplicate_rows":
        keep = op.get("keep", "first")
        if keep not in ("first", "last"):
            raise CleaningOperationError("'keep' must be first or last.")
        subset = None if (op.get("columns") in (None, "all") and not op.get("column")) else _target_columns(df, op)
        df = df.drop_duplicates(subset=subset, keep=keep)
        report["note"] = "Compared columns: " + (", ".join(subset) if subset else "all")

    elif op_type == "fill_missing":
        strategy = op.get("strategy", "fill_value")
        columns = _require_columns(df, op, "fill_missing")
        for col in columns:
            is_missing = df[col].map(_is_missing).astype(bool)
            if strategy == "drop_row":
                df = df[~is_missing]
            elif strategy == "fill_value":
                value = op.get("value")
                if not isinstance(value, str) or value.strip() == "":
                    raise CleaningOperationError("'fill_value' needs a non-empty 'value'.")
                df.loc[is_missing, col] = value
            elif strategy in ("fill_mean", "fill_median"):
                numbers = df.loc[~is_missing, col].map(lambda v: _parse_number(str(v), op.get("decimal_separator", ".")))
                invalid = numbers.isna()
                for raw in df.loc[~is_missing, col][invalid]:
                    skip(col, raw, "not a number - excluded from the calculation")
                valid = numbers.dropna().astype(float)
                if valid.empty:
                    raise CleaningOperationError(f"Column '{col}' has no numeric values to calculate a {strategy[5:]} from.")
                fill = valid.mean() if strategy == "fill_mean" else valid.median()
                df.loc[is_missing, col] = _format_number(round(float(fill), 4), "decimal")
            elif strategy == "fill_mode":
                present = df.loc[~is_missing, col]
                if present.empty:
                    raise CleaningOperationError(f"Column '{col}' has no values to take the most common one from.")
                counts = present.value_counts()
                top = counts[counts == counts.max()].index
                if len(top) > 1:
                    raise CleaningOperationError(
                        f"Column '{col}' has several equally common values ({', '.join(map(str, top[:3]))}); "
                        "choose one explicitly with fill_value."
                    )
                df.loc[is_missing, col] = top[0]
            else:
                raise CleaningOperationError(f"Invalid fill strategy: {strategy}")

    return df, report


def _diff(original: pd.DataFrame, result: pd.DataFrame) -> dict:
    """Compare by row identity (index label) and column name."""
    kept = original.index.intersection(result.index)
    shared_cols = [c for c in original.columns if c in result.columns]

    def canon(frame: pd.DataFrame) -> pd.DataFrame:
        # NaN and "" are both "missing": a cell going from NaN to NaN is not a change.
        return frame.astype(object).where(frame.notna(), None).map(lambda v: None if _is_missing(v) else v)

    before = canon(original.loc[kept, shared_cols])
    after = canon(result.loc[kept, shared_cols])
    changed = (before.values != after.values)
    per_column = {col: int(changed[:, i].sum()) for i, col in enumerate(shared_cols) if changed[:, i].any()}
    rows_removed = len(original) - len(kept)
    return {
        "values_changed": int(changed.sum()),
        "rows_modified": int(changed.any(axis=1).sum()),
        "rows_removed": rows_removed,
        "rows_changed": int(changed.any(axis=1).sum()) + rows_removed,
        "changed_columns": per_column,
        "_changed_labels": [kept[i] for i in changed.any(axis=1).nonzero()[0]],
        "_removed_labels": [label for label in original.index if label not in result.index],
    }


def potential_duplicate_count(df: pd.DataFrame) -> int:
    """Rows that are NOT exact duplicates but become duplicates once text is
    trimmed and lower-cased. Reported only - never removed or merged
    automatically, because "looks similar" is not "is the same record"."""
    if df.empty:
        return 0
    normalized = df.astype(object).map(lambda v: " ".join(v.split()).lower() if isinstance(v, str) else v)
    return int(normalized.duplicated(keep="first").sum() - df.duplicated(keep="first").sum())


def apply_operations(df: pd.DataFrame, operations: list[dict]) -> tuple[pd.DataFrame, dict]:
    """Apply operations in order. Returns the cleaned dataframe (fresh
    0..n-1 index, ready to save) and a summary used by both preview and
    apply."""
    if not operations:
        raise CleaningOperationError("At least one cleaning operation is required.")
    if len(operations) > 50:
        raise CleaningOperationError("At most 50 operations per run.")

    original = df.reset_index(drop=True)
    result = original
    reports = []
    for op in operations:
        before_rows = len(result)
        result, report = _apply_one(result, op)
        reports.append({
            "type": op.get("type"),
            "rows_removed": before_rows - len(result),
            **report,
        })

    diff = _diff(original, result)
    summary = {
        "original_row_count": len(original),
        "result_row_count": len(result),
        "rows_changed": diff["rows_changed"],
        "rows_modified": diff["rows_modified"],
        "rows_removed": diff["rows_removed"],
        "values_changed": diff["values_changed"],
        "changed_columns": diff["changed_columns"],
        "exact_duplicates_before": int(original.duplicated().sum()),
        "exact_duplicates_after": int(result.duplicated().sum()),
        "potential_duplicates_after": potential_duplicate_count(result),
        "operations_report": reports,
        "removes_rows": diff["rows_removed"] > 0,
        "_diff": diff,
        "_original": original,
        "_aligned": result,  # still carries the original row labels
    }
    return result.reset_index(drop=True), summary


def diff_sample(summary: dict, limit: int = 20) -> list[dict]:
    """Before/after pairs for changed rows, aligned by row identity, then a
    few removed rows (after = None). Row numbers are 1-based positions in
    the original file."""
    original = summary["_original"]
    aligned = summary["_aligned"]
    diff = summary["_diff"]
    shared_cols = [c for c in original.columns if c in aligned.columns]
    clean = lambda row: {k: (None if _is_missing(v) else v) for k, v in row.items()}  # noqa: E731
    samples = []
    for label in diff["_changed_labels"][:limit]:
        samples.append({
            "row": int(label) + 1,
            "before": clean(original.loc[label, shared_cols].to_dict()),
            "after": clean(aligned.loc[label, shared_cols].to_dict()),
        })
    for label in diff["_removed_labels"][: max(0, limit - len(samples))]:
        samples.append({"row": int(label) + 1, "before": clean(original.loc[label, shared_cols].to_dict()), "after": None})
    return samples


def public_summary(summary: dict) -> dict:
    return {k: v for k, v in summary.items() if not k.startswith("_")}
