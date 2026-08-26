from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
from uuid import UUID
from app.models.data_quality_rule import DataQualityDimension, RuleSeverity, RuleStatus


class DataQualityRuleBase(BaseModel):
    """Base schema for data quality rules"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    data_source: Optional[str] = Field(None, max_length=255)
    target_field: Optional[str] = Field(None, max_length=255)
    dimension: DataQualityDimension
    rule_type: str = Field(..., min_length=1, max_length=100)
    severity: RuleSeverity = RuleSeverity.MEDIUM
    status: RuleStatus = RuleStatus.DRAFT
    rule_definition: Optional[dict] = None
    owner_id: Optional[UUID] = None
    is_active: bool = True


class DataQualityRuleCreate(DataQualityRuleBase):
    """Schema for creating a data quality rule"""
    pass


class DataQualityRuleUpdate(BaseModel):
    """Schema for updating a data quality rule"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    data_source: Optional[str] = Field(None, max_length=255)
    target_field: Optional[str] = Field(None, max_length=255)
    dimension: Optional[DataQualityDimension] = None
    rule_type: Optional[str] = Field(None, min_length=1, max_length=100)
    severity: Optional[RuleSeverity] = None
    status: Optional[RuleStatus] = None
    rule_definition: Optional[dict] = None
    owner_id: Optional[UUID] = None
    is_active: Optional[bool] = None


class DataQualityRuleResponse(DataQualityRuleBase):
    """Schema for returning a data quality rule"""
    id: UUID
    created_by_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    owner_name: Optional[str] = None
    created_by_name: Optional[str] = None

    class Config:
        from_attributes = True


class DataQualityRuleListResponse(BaseModel):
    """Schema for returning a list of data quality rules"""
    items: List[DataQualityRuleResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class DataQualityResultBase(BaseModel):
    """Base schema for data quality results"""
    rule_id: UUID
    execution_timestamp: datetime
    status: str = Field(..., max_length=50)
    records_checked: Optional[int] = None
    records_passed: Optional[int] = None
    records_failed: Optional[int] = None
    execution_duration_ms: Optional[int] = None
    error_details: Optional[str] = None


class DataQualityResultCreate(DataQualityResultBase):
    """Schema for creating a data quality result"""
    pass


class DataQualityResultResponse(DataQualityResultBase):
    """Schema for returning a data quality result"""
    id: UUID
    created_at: datetime
    pass_rate: Optional[float] = None

    class Config:
        from_attributes = True


class DataQualityResultListResponse(BaseModel):
    """Schema for returning a list of data quality results"""
    items: List[DataQualityResultResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class DimensionStats(BaseModel):
    """Statistics for a data quality dimension"""
    dimension: DataQualityDimension
    total_rules: int
    active_rules: int
    passed_results: int
    failed_results: int
    last_execution: Optional[datetime] = None


class DataQualityMetrics(BaseModel):
    """Overall data quality metrics"""
    total_rules: int
    active_rules: int
    draft_rules: int
    total_results: int
    results_passed: int
    results_failed: int
    results_with_errors: int
    overall_pass_rate: float
    dimension_stats: List[DimensionStats]
    last_updated: datetime
