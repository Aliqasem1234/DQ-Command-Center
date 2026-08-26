"""Shared helpers for reading/writing the pandas DataFrame behind a
DatasetVersion's stored file. Every service that touches file content
(profiling, quality discovery, cleaning, preview, export) goes through
here so there is exactly one place that knows how CSV/XLSX are parsed.
"""
import pandas as pd

from app.services.file_storage_service import resolve_path


def read_dataframe(relative_path: str, file_format: str, nrows: int | None = None) -> pd.DataFrame:
    path = resolve_path(relative_path)
    if file_format == "csv":
        df = pd.read_csv(path, dtype=str, keep_default_na=True, na_values=["", "NA", "N/A", "null", "NULL"], nrows=nrows)
    elif file_format in ("xlsx", "xls"):
        df = pd.read_excel(path, dtype=str, engine="openpyxl" if file_format == "xlsx" else None, nrows=nrows)
    else:
        raise ValueError(f"Unsupported file format: {file_format}")
    # Normalize column names: strip whitespace, keep original casing/spacing
    # otherwise (users' real column headers), but guard against fully blank
    # header cells producing "Unnamed: N" columns from a stray trailing
    # comma/column in the source file.
    df.columns = [str(c).strip() for c in df.columns]
    return df


def write_dataframe(df: pd.DataFrame, relative_path: str, file_format: str) -> None:
    path = resolve_path(relative_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if file_format == "csv":
        df.to_csv(path, index=False)
    elif file_format in ("xlsx", "xls"):
        df.to_excel(path, index=False, engine="openpyxl")
    else:
        raise ValueError(f"Unsupported file format: {file_format}")
