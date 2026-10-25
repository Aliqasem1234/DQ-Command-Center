from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import List, Optional
from datetime import datetime


class RegisterRequest(BaseModel):
    email: EmailStr
    # The registration form doesn't ask for a username, so it is optional:
    # when omitted the server derives a unique one from the email address.
    # Deriving it client-side meant short local-parts ("ab@x.se") and shared
    # local-parts across domains failed on a field the user never saw.
    username: Optional[str] = Field(default=None, min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)

    @field_validator("full_name")
    @classmethod
    def full_name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Full name must not be blank")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    full_name: str
    department: Optional[str] = None
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    is_active: bool
    is_verified: bool
    is_super_admin: bool
    created_at: datetime
    roles: List[str] = []
    # Effective permission codes, so the frontend can gate navigation and
    # actions on the same codes the backend enforces (UX only - the backend
    # remains the security boundary).
    permissions: List[str] = []

    model_config = {"from_attributes": True}


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=128)


class VerifyEmailRequest(BaseModel):
    token: str


class UpdateProfileRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class MessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None


class ChangePasswordResponse(BaseModel):
    message: str
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
