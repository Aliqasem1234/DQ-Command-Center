"""
Data profiling: computes real column- and dataset-level statistics from an
uploaded file and persists them onto the existing DataElement /
DataElementMetadata models. Nothing here is estimated or faked - every
number comes from actually reading the file with pandas.
"""
import logging
import re
from datetime import datetime, timezone
from uuid import UUID

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.data_hierarchy import Dataset, DataElement, DataElementMetadata, DatasetVersion, DatasetVersionStatus
from app.services.dataframe_io import read_dataframe

logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
INT_RE = re.compile(r"^-?\d+$")
FLOAT_RE = re.compile(r"^-?\d+\.\d+$")


def infer_column_type(series: pd.Series) -> str:
    """Infer a simple logical type from a string-typed pandas Series by
    sampling non-null values, rather than trusting pandas' own dtype
    inference (which would silently coerce or drop invalid values before
    we ever get a chance to flag them as a quality problem).

    Thresholds are deliberately lenient (well under 100%): the entire point
    of this tool is to find the invalid minority in an otherwise-typed
    column, so a strict threshold that reclassifies a "mostly dates, a few
    garbage values" column as plain "string" the moment it gets too dirty
    would defeat the purpose - it's exactly the dirty columns we most need
    to keep classified so the validity checks in quality_discovery_service
    actually run against them.
    """
    non_null = series.dropna()
    if len(non_null) == 0:
        return "string"

    sample = non_null.astype(str).str.strip()
    sample = sample[sample != ""]
    if len(sample) == 0:
        return "string"

    n = len(sample)
    if (sample.str.match(INT_RE)).sum() / n >= 0.6:
        return "integer"
    if (sample.str.match(FLOAT_RE)).sum() / n >= 0.6:
        return "float"
    if (sample.str.lower().isin(["true", "false", "0", "1", "yes", "no"])).sum() / n >= 0.9:
        return "boolean"
    try:
        parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
        if parsed.notna().sum() / n >= 0.5:
            return "datetime"
    except (ValueError, TypeError):
        pass
    if (sample.str.match(EMAIL_RE)).sum() / n >= 0.5:
        return "email"
    return "string"


def profile_column(series: pd.Series) -> dict:
    total = len(series)
    non_null = series.dropna()
    non_null_str = non_null.astype(str)
    null_count = total - len(non_null)
    unique_count = non_null.nunique()
    duplicate_count = max(0, len(non_null) - unique_count)

    lengths = non_null_str.str.len()
    sample_values = non_null_str.drop_duplicates().head(5).tolist()

    stats = {
        "value_count": total,
        "null_count": int(null_count),
        "unique_count": int(unique_count),
        "duplicate_count": int(duplicate_count),
        "min_length": int(lengths.min()) if len(lengths) else None,
        "max_length": int(lengths.max()) if len(lengths) else None,
        "sample_values": sample_values,
        "min_value": None,
        "max_value": None,
        "average_value": None,
    }

    inferred_type = infer_column_type(series)
    if inferred_type in ("integer", "float"):
        numeric = pd.to_numeric(non_null_str, errors="coerce")
        numeric = numeric.dropna()
        if len(numeric):
            stats["min_value"] = str(numeric.min())
            stats["max_value"] = str(numeric.max())
            stats["average_value"] = float(numeric.mean())
    elif len(non_null_str):
        stats["min_value"] = str(sorted(non_null_str.unique())[0]) if unique_count else None
        stats["max_value"] = str(sorted(non_null_str.unique())[-1]) if unique_count else None

    return {**stats, "inferred_type": inferred_type}


async def profile_dataset_version(
    db: AsyncSession,
    version: DatasetVersion,
) -> dict:
    """Read the version's file, compute real per-column and dataset-level
    profiling stats, persist them on DataElement/DataElementMetadata, and
    return a summary dict for the API response."""
    version.status = DatasetVersionStatus.PROFILING
    await db.flush()

    try:
        df = read_dataframe(version.file_path, version.file_format)
    except Exception as e:
        version.status = DatasetVersionStatus.ERROR
        version.error_message = f"Failed to read file: {e}"
        await db.commit()
        raise

    version.row_count = len(df)
    version.column_count = len(df.columns)

    dataset_result = await db.execute(select(Dataset).where(Dataset.id == version.dataset_id))
    dataset = dataset_result.scalar_one()
    dataset.row_count = len(df)
    dataset.last_updated = datetime.now(timezone.utc)

    existing_result = await db.execute(select(DataElement).where(DataElement.dataset_id == dataset.id))
    existing_elements = {el.name: el for el in existing_result.scalars().all()}

    now = datetime.now(timezone.utc)
    column_profiles = []

    for position, column_name in enumerate(df.columns):
        column_profile = profile_column(df[column_name])
        column_profiles.append({"name": column_name, **column_profile})

        element = existing_elements.get(column_name)
        if element is None:
            element = DataElement(
                dataset_id=dataset.id,
                name=column_name,
                data_type=column_profile["inferred_type"],
                column_position=position,
                nullable=column_profile["null_count"] > 0,
                is_primary_key=(column_profile["unique_count"] == column_profile["value_count"] - column_profile["null_count"] and column_profile["value_count"] > 0),
                created_at=now,
                updated_at=now,
            )
            db.add(element)
            await db.flush()
        else:
            element.data_type = column_profile["inferred_type"]
            element.column_position = position
            element.nullable = column_profile["null_count"] > 0
            element.updated_at = now

        meta_result = await db.execute(
            select(DataElementMetadata).where(DataElementMetadata.element_id == element.id)
        )
        metadata = meta_result.scalar_one_or_none()
        if metadata is None:
            metadata = DataElementMetadata(element_id=element.id, created_at=now, updated_at=now)
            db.add(metadata)

        metadata.sample_values = column_profile["sample_values"]
        metadata.min_length = column_profile["min_length"]
        metadata.max_length = column_profile["max_length"]
        metadata.value_count = column_profile["value_count"]
        metadata.null_count = column_profile["null_count"]
        metadata.unique_count = column_profile["unique_count"]
        metadata.duplicate_count = column_profile["duplicate_count"]
        metadata.min_value = column_profile["min_value"]
        metadata.max_value = column_profile["max_value"]
        metadata.average_value = column_profile["average_value"]
        metadata.last_profiled = now
        metadata.updated_at = now

    version.status = DatasetVersionStatus.PROFILED
    await db.commit()

    return {
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": column_profiles,
    }
