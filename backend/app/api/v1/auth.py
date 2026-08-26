from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user_from_token
from app.models.user import User
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
    UpdateProfileRequest,
    ChangePasswordRequest,
    MessageResponse,
    UserResponse,
)
from app.services import auth_service
from app.config import settings
from app.core.limiter import limiter

router = APIRouter()


def _get_client_info(request: Request):
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return ip_address, user_agent


@router.post(
    "/auth/register",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
@limiter.limit("5/minute")
async def register(
    request: Request,
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        user, token = await auth_service.register_user(
            db,
            email=body.email,
            username=body.username,
            password=body.password,
            full_name=body.full_name,
        )
        return MessageResponse(
            message="Registration successful. Please check your email to verify your account.",
            detail=f"Verification token: {token}" if settings.ENVIRONMENT == "development" else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/auth/login",
    response_model=LoginResponse,
    summary="Login with email and password",
)
@limiter.limit("10/minute")
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    ip_address, user_agent = _get_client_info(request)
    try:
        user, access_token, refresh_token = await auth_service.login_user(
            db,
            email=body.email,
            password=body.password,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=auth_service.user_to_response(user),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post(
    "/auth/refresh",
    response_model=RefreshTokenResponse,
    summary="Refresh access token using refresh token",
)
async def refresh_token(
    body: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        access_token, new_refresh_token = await auth_service.refresh_user_tokens(
            db, body.refresh_token
        )
        return RefreshTokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post(
    "/auth/logout",
    response_model=MessageResponse,
    summary="Logout by revoking refresh token",
)
async def logout(
    body: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    success = await auth_service.logout_user(db, body.refresh_token)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")
    return MessageResponse(message="Logged out successfully")


@router.post(
    "/auth/forgot-password",
    response_model=MessageResponse,
    summary="Request password reset email",
)
@limiter.limit("3/minute")
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    token = await auth_service.forgot_password(db, body.email)
    return MessageResponse(
        message="If the email exists, a password reset link has been sent.",
        detail=f"Reset token: {token}" if settings.ENVIRONMENT == "development" and token else None,
    )


@router.post(
    "/auth/reset-password",
    response_model=MessageResponse,
    summary="Reset password using token",
)
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        await auth_service.reset_password(db, body.token, body.password)
        return MessageResponse(message="Password reset successful")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/auth/verify-email",
    response_model=MessageResponse,
    summary="Verify email using token",
)
async def verify_email(
    body: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        await auth_service.verify_email(db, body.token)
        return MessageResponse(message="Email verified successfully")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/auth/change-password",
    response_model=MessageResponse,
    summary="Change password for authenticated user",
)
async def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
):
    try:
        await auth_service.change_password(
            db, current_user, body.current_password, body.new_password
        )
        return MessageResponse(message="Password changed successfully")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/auth/me",
    response_model=UserResponse,
    summary="Get current authenticated user",
)
async def get_current_user_endpoint(
    current_user: User = Depends(get_current_user_from_token),
):
    return auth_service.user_to_response(current_user)


@router.put(
    "/auth/me",
    response_model=UserResponse,
    summary="Update the current authenticated user's own profile",
)
async def update_profile(
    body: UpdateProfileRequest,
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
):
    user = await auth_service.update_profile(db, current_user, body.full_name)
    return auth_service.user_to_response(user)
