from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=255)


class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None


class DepartmentResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    user_count: int = 0

    model_config = {"from_attributes": True}


class DepartmentListResponse(BaseModel):
    items: List[DepartmentResponse]
    total: int
    page: int
    page_size: int
