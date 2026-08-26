"""
Data cleaning operations.

Every operation here is applied to an in-memory copy of the dataframe and
returns a diff summary alongside the result - callers decide whether to
just preview that diff or actually persist it as a new DatasetVersion.
The source file is never touched.
"""
from typing import Any, Literal, TypedDict

import pandas as pd

VALID_OPERATION_TYPES = {
    "trim_whitespace",
    "collapse_whitespace",
    "standardize_case",
    "normalize_dates",
    "remove_duplicate_rows",
    "fill_missing",
}


class CleaningOperationError(ValueError):
    pass


def _target_columns(df: pd.DataFrame, op: dict) -> list[str]:
    # Every dataframe reaching this module was loaded via read_dataframe()
    # with dtype=str, so "all" means every column - deliberately not
    # filtered by pandas dtype, since pandas 3.x's default string dtype
    # isn't `object` the way pandas 2.x's was, and checking for object
    # dtype specifically silently matched nothing under 3.x.
    columns = op.get("columns") or ([op["column"]] if op.get("column") else None)
    if columns is None or columns == "all":
        return list(df.columns)
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise CleaningOperationError(f"Unknown column(s): {', '.join(missing)}")
    return columns


def _apply_one(df: pd.DataFrame, op: dict) -> pd.DataFrame:
    op_type = op.get("type")
    if op_type not in VALID_OPERATION_TYPES:
        raise CleaningOperationError(f"Unknown operation type: {op_type}")

    df = df.copy()

    if op_type == "trim_whitespace":
        for col in _target_columns(df, op):
            df[col] = df[col].apply(lambda v: v.strip() if isinstance(v, str) else v)

    elif op_type == "collapse_whitespace":
        for col in _target_columns(df, op):
            df[col] = df[col].apply(
                lambda v: " ".join(v.split()) if isinstance(v, str) else v
            )

    elif op_type == "standardize_case":
        case = op.get("case", "lower")
        if case not in ("lower", "upper", "title"):
            raise CleaningOperationError(f"Invalid case '{case}' - expected lower/upper/title")
        for col in _target_columns(df, op):
            if case == "lower":
                df[col] = df[col].apply(lambda v: v.lower() if isinstance(v, str) else v)
            elif case == "upper":
                df[col] = df[col].apply(lambda v: v.upper() if isinstance(v, str) else v)
            else:
                df[col] = df[col].apply(lambda v: v.title() if isinstance(v, str) else v)

    elif op_type == "normalize_dates":
        target_format = op.get("target_format", "%Y-%m-%d")
        for col in _target_columns(df, op):
            parsed = pd.to_datetime(df[col], errors="coerce", format="mixed")
            df[col] = parsed.dt.strftime(target_format).where(parsed.notna(), df[col])

    elif op_type == "remove_duplicate_rows":
        df = df.drop_duplicates(keep="first").reset_index(drop=True)

    elif op_type == "fill_missing":
        strategy = op.get("strategy", "fill_value")
        columns = _target_columns(df, op)
        for col in columns:
            is_missing = df[col].isna() | (df[col].astype(str).str.strip() == "")
            if strategy == "drop_row":
                df = df[~is_missing]
            elif strategy == "fill_value":
                df.loc[is_missing, col] = op.get("value", "")
            elif strategy in ("fill_mean", "fill_median", "fill_mode"):
                numeric = pd.to_numeric(df[col], errors="coerce")
                if strategy == "fill_mean":
                    fill_value = numeric.mean()
                elif strategy == "fill_median":
                    fill_value = numeric.median()
                else:
                    mode = df.loc[~is_missing, col].mode()
                    fill_value = mode.iloc[0] if len(mode) else ""
                df.loc[is_missing, col] = fill_value
            else:
                raise CleaningOperationError(f"Invalid fill strategy: {strategy}")
        df = df.reset_index(drop=True)

    return df


def apply_operations(df: pd.DataFrame, operations: list[dict]) -> tuple[pd.DataFrame, dict]:
    """Apply a sequence of cleaning operations, returning the resulting
    dataframe and a diff summary against the original."""
    if not operations:
        raise CleaningOperationError("At least one cleaning operation is required.")

    original = df.reset_index(drop=True)
    result = original
    for op in operations:
        result = _apply_one(result, op)

    rows_changed, values_changed = _diff_summary(original, result)

    return result, {
        "original_row_count": len(original),
        "result_row_count": len(result),
        "rows_changed": rows_changed,
        "values_changed": values_changed,
    }


def _diff_summary(original: pd.DataFrame, result: pd.DataFrame) -> tuple[int, int]:
    """Best-effort diff between two dataframes that may differ in row count
    (e.g. dedup/drop_row). Compares row-by-row up to the shared length by
    position - good enough for a change summary, not a true alignment."""
    shared_rows = min(len(original), len(result))
    shared_cols = [c for c in original.columns if c in result.columns]
    if shared_rows == 0 or not shared_cols:
        return abs(len(original) - len(result)), 0

    orig_slice = original.iloc[:shared_rows][shared_cols].astype(str)
    result_slice = result.iloc[:shared_rows][shared_cols].astype(str)
    diff_mask = orig_slice.values != result_slice.values
    values_changed = int(diff_mask.sum())
    rows_changed = int((diff_mask.any(axis=1)).sum())
    rows_changed += abs(len(original) - len(result))
    return rows_changed, values_changed


def diff_sample(original: pd.DataFrame, result: pd.DataFrame, limit: int = 20) -> list[dict]:
    """Return up to `limit` sample rows that actually changed, as
    {before, after} pairs, for a human to review before committing.

    Finds the changed row positions with a single vectorized comparison
    first, then only builds {before, after} dicts for at most `limit` rows -
    row-by-row .iloc access in a Python loop over every row is prohibitively
    slow on larger datasets (seconds on 20k+ rows), especially when few or
    no rows actually changed and a naive loop would still scan all of them.
    """
    shared_rows = min(len(original), len(result))
    shared_cols = [c for c in original.columns if c in result.columns]
    if shared_rows == 0 or not shared_cols:
        return []

    orig_slice = original.iloc[:shared_rows][shared_cols].astype(str)
    result_slice = result.iloc[:shared_rows][shared_cols].astype(str)
    row_changed = (orig_slice.values != result_slice.values).any(axis=1)
    changed_positions = row_changed.nonzero()[0][:limit]

    samples = []
    for pos in changed_positions:
        before = original.iloc[int(pos)][shared_cols]
        after = result.iloc[int(pos)][shared_cols]
        samples.append({"before": before.to_dict(), "after": after.to_dict()})
    return samples
