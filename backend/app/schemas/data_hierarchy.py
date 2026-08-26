"""
Schemas for reorganized data hierarchy API
Pydantic models for validation and serialization
"""

from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


# ===== DATA DOMAIN SCHEMAS =====

class DataDomainBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)


class DataDomainCreate(DataDomainBase):
    business_owner_id: Optional[UUID] = None
    domain_steward_id: Optional[UUID] = None


class DataDomainUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    business_owner_id: Optional[UUID] = None
    domain_steward_id: Optional[UUID] = None


class DataDomainResponse(DataDomainBase):
    id: UUID
    business_owner_id: Optional[UUID]
    domain_steward_id: Optional[UUID]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DataDomainDetailResponse(DataDomainResponse):
    dataset_count: Optional[int] = None


# ===== DATASET SCHEMAS =====

class DatasetBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    business_definition: Optional[str] = None
    dataset_type: str


class DatasetCreate(DatasetBase):
    domain_id: UUID
    data_source_system: Optional[str] = None
    database_name: Optional[str] = None
    table_name: Optional[str] = None
    classification: Optional[str] = "internal"
    data_owner_id: Optional[UUID] = None
    data_steward_id: Optional[UUID] = None


class DatasetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    business_definition: Optional[str] = None
    classification: Optional[str] = None
    data_owner_id: Optional[UUID] = None
    data_steward_id: Optional[UUID] = None
    row_count: Optional[int] = None
    last_updated: Optional[datetime] = None


class DatasetResponse(DatasetBase):
    id: UUID
    domain_id: UUID
    data_source_system: Optional[str]
    database_name: Optional[str]
    table_name: Optional[str]
    classification: str
    data_owner_id: Optional[UUID]
    data_steward_id: Optional[UUID]
    row_count: Optional[int]
    last_updated: Optional[datetime]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DatasetDetailResponse(DatasetResponse):
    element_count: Optional[int] = None
    rule_count: Optional[int] = None
    issue_count: Optional[int] = None
    health_score: Optional[float] = None


# ===== DATA ELEMENT SCHEMAS =====

class DataElementBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    data_type: str
    description: Optional[str] = None
    business_term: Optional[str] = None
    business_definition: Optional[str] = None


class DataElementCreate(DataElementBase):
    dataset_id: UUID
    column_position: Optional[int] = None
    is_primary_key: bool = False
    is_foreign_key: bool = False
    nullable: bool = True
    classification: Optional[str] = "internal"
    data_owner_id: Optional[UUID] = None


class DataElementUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    business_term: Optional[str] = None
    business_definition: Optional[str] = None
    classification: Optional[str] = None


class DataElementResponse(DataElementBase):
    id: UUID
    dataset_id: UUID
    column_position: Optional[int]
    is_primary_key: bool
    is_foreign_key: bool
    nullable: bool
    classification: str
    data_owner_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===== METADATA SCHEMAS =====

class DataElementMetadataResponse(BaseModel):
    element_id: UUID
    sample_values: Optional[List[str]] = None
    format_pattern: Optional[str] = None
    allowed_values: Optional[Dict[str, Any]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    value_count: Optional[int] = None
    null_count: Optional[int] = None
    unique_count: Optional[int] = None
    duplicate_count: Optional[int] = None
    min_value: Optional[str] = None
    max_value: Optional[str] = None
    average_value: Optional[float] = None
    last_profiled: Optional[datetime] = None

    class Config:
        from_attributes = True


# ===== QUALITY RULE SCHEMAS =====

class QualityRuleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    dimension: str
    rule_type: str


class QualityRuleCreate(QualityRuleBase):
    dataset_id: Optional[UUID] = None
    element_id: Optional[UUID] = None
    severity: str = "medium"
    status: str = "draft"
    target_level: Optional[str] = None
    quality_threshold: Optional[float] = None
    sla_hours: Optional[int] = None
    rule_definition: Optional[Dict[str, Any]] = None
    owner_id: Optional[UUID] = None


class QualityRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    quality_threshold: Optional[float] = None
    sla_hours: Optional[int] = None


class QualityRuleResponse(QualityRuleBase):
    id: UUID
    dataset_id: Optional[UUID]
    element_id: Optional[UUID]
    severity: str
    status: str
    target_level: Optional[str]
    quality_threshold: Optional[float]
    sla_hours: Optional[int]
    owner_id: Optional[UUID]
    created_by_id: Optional[UUID]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===== QUALITY ISSUE SCHEMAS =====

class QualityIssueBase(BaseModel):
    severity: str
    description: Optional[str] = None


class QualityIssueCreate(QualityIssueBase):
    rule_id: UUID
    dataset_id: UUID
    assigned_to_id: Optional[UUID] = None


class QualityIssueUpdate(BaseModel):
    severity: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    assigned_to_id: Optional[UUID] = None
    resolution_notes: Optional[str] = None


class QualityIssueSummaryResponse(BaseModel):
    id: UUID
    description: Optional[str] = None
    severity: str
    status: str
    dataset_name: Optional[str] = None
    detected_at: datetime

    class Config:
        from_attributes = True


class QualityIssueResponse(QualityIssueBase):
    id: UUID
    rule_id: UUID
    dataset_id: UUID
    status: str
    detected_at: datetime
    assigned_to_id: Optional[UUID]
    resolved_at: Optional[datetime]
    resolution_notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===== GOVERNANCE SCHEMAS =====

class GovernanceAssignmentBase(BaseModel):
    role: str
    responsibility_description: Optional[str] = None


class GovernanceAssignmentCreate(GovernanceAssignmentBase):
    domain_id: Optional[UUID] = None
    dataset_id: Optional[UUID] = None
    element_id: Optional[UUID] = None
    user_id: UUID
    department_id: Optional[UUID] = None


class GovernanceAssignmentUpdate(BaseModel):
    role: Optional[str] = None
    responsibility_description: Optional[str] = None
    is_active: Optional[bool] = None


class GovernanceAssignmentResponse(GovernanceAssignmentBase):
    id: UUID
    domain_id: Optional[UUID]
    dataset_id: Optional[UUID]
    element_id: Optional[UUID]
    user_id: UUID
    department_id: Optional[UUID]
    is_active: bool
    assigned_date: datetime

    class Config:
        from_attributes = True


# ===== QUALITY TARGET SCHEMAS =====

class QualityTargetBase(BaseModel):
    dimension: str
    target_score: float = Field(..., ge=0, le=100)
    minimum_score: float = Field(..., ge=0, le=100)


class QualityTargetCreate(QualityTargetBase):
    dataset_id: Optional[UUID] = None
    element_id: Optional[UUID] = None
    sla_hours: Optional[int] = None


class QualityTargetResponse(QualityTargetBase):
    id: UUID
    dataset_id: Optional[UUID]
    element_id: Optional[UUID]
    sla_hours: Optional[int]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# ===== ANALYTICS SCHEMAS =====

class HealthScoreResponse(BaseModel):
    health_score: float = Field(..., ge=0, le=100)
    status: str  # excellent, good, fair, poor, critical
    active_rules: Optional[int] = None
    calculation_basis: str


class DimensionScoreResponse(BaseModel):
    dimension: str
    score: Optional[float] = Field(None, ge=0, le=100)
    status: str
    rule_count: int


class QualityTrendResponse(BaseModel):
    date: str
    pass_rate: float = Field(..., ge=0, le=100)
    total_runs: int


class QualityTrendsResponse(BaseModel):
    trend: str  # improving, stable, degrading
    period_days: int
    total_check_runs: int
    daily_data: List[QualityTrendResponse]


class IssueAnalyticsResponse(BaseModel):
    open_issues: int
    in_progress_issues: int
    critical_count: int
    high_count: int
    by_severity: Dict[str, int]


class DashboardHealthResponse(BaseModel):
    health_score: float = Field(..., ge=0, le=100)
    status: str
    dimensions: Dict[str, DimensionScoreResponse]
    open_issues: int
    critical_issues: int
    recent_trend: str
    total_datasets: int = 0
    total_quality_rules: int = 0
    daily_trend: List[QualityTrendResponse] = []


# ===== SEARCH SCHEMAS =====

class SearchResultsResponse(BaseModel):
    domains: List[DataDomainResponse] = []
    datasets: List[DatasetResponse] = []
    elements: List[DataElementResponse] = []
    total_results: int


# ===== PAGINATION =====

class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
