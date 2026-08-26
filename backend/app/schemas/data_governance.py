from pydantic import BaseModel, Field, model_validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from app.models.data_hierarchy import GovernanceRole, GovernancePolicyStatus


class GovernanceAssignmentBase(BaseModel):
    """Base schema for a governance role assignment (owner/steward/curator/analyst)"""
    domain_id: Optional[UUID] = None
    dataset_id: Optional[UUID] = None
    element_id: Optional[UUID] = None
    role: GovernanceRole
    user_id: UUID
    department_id: Optional[UUID] = None
    responsibility_description: Optional[str] = Field(None, max_length=2000)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: bool = True

    @model_validator(mode="after")
    def _exactly_one_scope(self) -> "GovernanceAssignmentBase":
        scopes = [self.domain_id, self.dataset_id, self.element_id]
        if sum(1 for s in scopes if s is not None) != 1:
            raise ValueError("Exactly one of domain_id, dataset_id, element_id must be set")
        return self


class GovernanceAssignmentCreate(GovernanceAssignmentBase):
    pass


class GovernanceAssignmentUpdate(BaseModel):
    responsibility_description: Optional[str] = Field(None, max_length=2000)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None


class GovernanceAssignmentResponse(BaseModel):
    id: UUID
    domain_id: Optional[UUID] = None
    dataset_id: Optional[UUID] = None
    element_id: Optional[UUID] = None
    role: GovernanceRole
    user_id: UUID
    user_name: Optional[str] = None
    department_id: Optional[UUID] = None
    responsibility_description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: bool
    assigned_date: datetime
    scope_name: Optional[str] = None

    model_config = {"from_attributes": True}


class GovernanceAssignmentListResponse(BaseModel):
    items: List[GovernanceAssignmentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class GovernancePolicyBase(BaseModel):
    """Base schema for governance policies scoped to a domain or dataset"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    domain_id: Optional[UUID] = None
    dataset_id: Optional[UUID] = None
    policy_type: str = Field(..., min_length=1, max_length=100)
    policy_definition: Optional[dict] = None
    status: GovernancePolicyStatus = GovernancePolicyStatus.DRAFT
    effective_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None

    @model_validator(mode="after")
    def _exactly_one_scope(self) -> "GovernancePolicyBase":
        scopes = [self.domain_id, self.dataset_id]
        if sum(1 for s in scopes if s is not None) != 1:
            raise ValueError("Exactly one of domain_id, dataset_id must be set")
        return self


class GovernancePolicyCreate(GovernancePolicyBase):
    pass


class GovernancePolicyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    policy_type: Optional[str] = None
    policy_definition: Optional[dict] = None
    status: Optional[GovernancePolicyStatus] = None
    effective_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None


class GovernancePolicyResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    domain_id: Optional[UUID] = None
    dataset_id: Optional[UUID] = None
    policy_type: str
    policy_definition: Optional[dict] = None
    status: GovernancePolicyStatus
    effective_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    created_by_id: Optional[UUID] = None
    created_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GovernancePolicyListResponse(BaseModel):
    items: List[GovernancePolicyResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
