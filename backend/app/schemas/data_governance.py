from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from app.models.data_governance import ClassificationLevel, GovernanceStatus


class DataAssetBase(BaseModel):
    """Base schema for data assets"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    business_definition: Optional[str] = Field(None)
    asset_type: str = Field(..., min_length=1, max_length=100)
    data_source: Optional[str] = Field(None, max_length=255)
    database_name: Optional[str] = Field(None, max_length=255)
    table_or_collection: Optional[str] = Field(None, max_length=255)
    classification: ClassificationLevel = ClassificationLevel.INTERNAL
    status: GovernanceStatus = GovernanceStatus.DRAFT
    data_owner_id: Optional[UUID] = None
    data_steward_id: Optional[UUID] = None
    retention_days: Optional[int] = None
    is_active: bool = True


class DataAssetCreate(DataAssetBase):
    """Schema for creating data assets"""
    pass


class DataAssetUpdate(BaseModel):
    """Schema for updating data assets"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None)
    business_definition: Optional[str] = None
    classification: Optional[ClassificationLevel] = None
    status: Optional[GovernanceStatus] = None
    data_owner_id: Optional[UUID] = None
    data_steward_id: Optional[UUID] = None
    retention_days: Optional[int] = None
    is_active: Optional[bool] = None


class DataAssetResponse(DataAssetBase):
    """Schema for returning data assets"""
    id: UUID
    created_at: datetime
    updated_at: datetime
    data_owner_name: Optional[str] = None
    data_steward_name: Optional[str] = None

    class Config:
        from_attributes = True


class DataAssetListResponse(BaseModel):
    """Schema for returning list of data assets"""
    items: List[DataAssetResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class GovernancePolicyBase(BaseModel):
    """Base schema for governance policies"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None)
    data_asset_id: Optional[UUID] = None
    department_id: Optional[UUID] = None
    policy_type: str = Field(..., min_length=1, max_length=100)
    policy_definition: Optional[dict] = None
    status: GovernanceStatus = GovernanceStatus.DRAFT
    effective_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None


class GovernancePolicyCreate(GovernancePolicyBase):
    """Schema for creating policies"""
    pass


class GovernancePolicyUpdate(BaseModel):
    """Schema for updating policies"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    policy_type: Optional[str] = None
    policy_definition: Optional[dict] = None
    status: Optional[GovernanceStatus] = None
    effective_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None


class GovernancePolicyResponse(GovernancePolicyBase):
    """Schema for returning policies"""
    id: UUID
    created_by_id: Optional[UUID] = None
    created_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GovernancePolicyListResponse(BaseModel):
    """Schema for returning list of policies"""
    items: List[GovernancePolicyResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class DataStewardshipBase(BaseModel):
    """Base schema for data stewardship"""
    data_asset_id: UUID
    user_id: UUID
    department_id: Optional[UUID] = None
    responsibility_type: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: bool = True


class DataStewardshipCreate(DataStewardshipBase):
    """Schema for creating stewardship"""
    pass


class DataStewardshipUpdate(BaseModel):
    """Schema for updating stewardship"""
    responsibility_type: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None


class DataStewardshipResponse(DataStewardshipBase):
    """Schema for returning stewardship"""
    id: UUID
    assigned_date: datetime
    user_name: Optional[str] = None
    data_asset_name: Optional[str] = None

    class Config:
        from_attributes = True


class DataStewardshipListResponse(BaseModel):
    """Schema for returning list of stewardships"""
    items: List[DataStewardshipResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
