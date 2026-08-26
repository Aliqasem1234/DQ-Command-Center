from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class DashboardStats(BaseModel):
    total_users: int
    active_users: int
    roles_count: int
    departments_count: int
    audit_events_today: int


class RegistrationDataPoint(BaseModel):
    date: str
    count: int


class LoginDataPoint(BaseModel):
    date: str
    count: int


class RecentActivityItem(BaseModel):
    id: str
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    action: str
    entity_type: str
    created_at: datetime


class DashboardResponse(BaseModel):
    stats: DashboardStats
    registration_chart: List[RegistrationDataPoint]
    login_chart: List[LoginDataPoint]
    recent_activity: List[RecentActivityItem]
