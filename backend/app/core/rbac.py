from fastapi import Depends, HTTPException, status
from typing import List, Callable
from app.dependencies import get_current_user_from_token
from app.models.user import User


def require_roles(allowed_roles: List[str]):
    async def role_checker(current_user: User = Depends(get_current_user_from_token)) -> User:
        if current_user.is_super_admin:
            return current_user

        user_role_names = [ur.role.name for ur in current_user.roles if ur.role]
        for role_name in user_role_names:
            if role_name in allowed_roles:
                return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return role_checker


def require_permission(permission_code: str):
    async def permission_checker(current_user: User = Depends(get_current_user_from_token)) -> User:
        if current_user.is_super_admin:
            return current_user

        for user_role in current_user.roles:
            if user_role.role:
                for rp in user_role.role.role_permissions:
                    if rp.permission and rp.permission.code == permission_code:
                        return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return permission_checker
