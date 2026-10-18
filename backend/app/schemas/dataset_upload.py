from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from uuid import UUID


class DatasetVersionResponse(BaseModel):
    id: UUID
    dataset_id: UUID
    version_number: int
    original_filename: Optional[str] = None
    file_format: str
    file_size_bytes: Optional[int] = None
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    is_original: bool
    source_version_id: Optional[UUID] = None
    cleaning_operations: Optional[list] = None
    rows_changed: Optional[int] = None
    values_changed: Optional[int] = None
    status: str
    quality_score: Optional[float] = None
    error_message: Optional[str] = None
    created_by_id: Optional[UUID] = None
    created_by_name: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ColumnProfileResponse(BaseModel):
    name: str
    inferred_type: str
    value_count: int
    null_count: int
    unique_count: int
    duplicate_count: int
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    min_value: Optional[str] = None
    max_value: Optional[str] = None
    average_value: Optional[float] = None
    sample_values: List[str] = []


class ProfileSummaryResponse(BaseModel):
    row_count: int
    column_count: int
    columns: List[ColumnProfileResponse]


class ScanResultResponse(BaseModel):
    checks_run: int
    issues_found: int
    issues_resolved: int
    custom_rules_run: int = 0
    # None for an empty table (nothing to measure).
    quality_score: Optional[float] = None


class CleaningOperation(BaseModel):
    type: str
    columns: Optional[Union[List[str], str]] = None  # a list of names, or the literal "all"
    column: Optional[str] = None
    case: Optional[str] = None
    target_format: Optional[str] = None
    source_format: Optional[str] = None
    day_first: Optional[bool] = None
    strategy: Optional[str] = None
    value: Optional[Any] = None
    target: Optional[str] = None
    on_invalid: Optional[str] = None
    decimal_separator: Optional[str] = None
    mapping: Optional[Dict[str, str]] = None
    case_sensitive: Optional[bool] = None
    keep: Optional[str] = None


class CleaningRequest(BaseModel):
    operations: List[CleaningOperation] = Field(..., min_length=1)


class CleaningPreviewResponse(BaseModel):
    original_row_count: int
    result_row_count: int
    rows_changed: int
    rows_modified: int = 0
    rows_removed: int = 0
    values_changed: int
    changed_columns: Dict[str, int] = {}
    exact_duplicates_before: int = 0
    exact_duplicates_after: int = 0
    potential_duplicates_after: int = 0
    operations_report: List[dict] = []
    removes_rows: bool = False
    # Same scoring as a scan, computed on the data before and after the
    # operations. None when there is nothing to score (empty table).
    quality_score_before: Optional[float] = None
    quality_score_after: Optional[float] = None
    sample_changes: List[dict]


class VersionQualitySummary(BaseModel):
    version_id: UUID
    version_number: int
    is_original: bool
    quality_score: Optional[float] = None
    row_count: Optional[int] = None
    created_at: datetime


class QualityComparisonResponse(BaseModel):
    dataset_id: UUID
    versions: List[VersionQualitySummary]
