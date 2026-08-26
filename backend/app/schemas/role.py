from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class PermissionResponse(BaseModel):
    id: str
    name: str
    code: str
    module: str
    description: Optional[str] = None

    model_config = {"from_attributes": True}


class RoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    permission_ids: List[str] = []


class RoleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=255)


class RoleResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    is_system: bool
    created_at: datetime
    updated_at: datetime
    user_count: int = 0
    permissions: List[PermissionResponse] = []

    model_config = {"from_attributes": True}


class RoleListResponse(BaseModel):
    items: List[RoleResponse]
    total: int
    page: int
    page_size: int


class RolePermissionsUpdate(BaseModel):
    permission_ids: List[str]
