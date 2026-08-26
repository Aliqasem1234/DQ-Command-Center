from fastapi import APIRouter, Depends
from app.dependencies import get_current_user_from_token
from app.core.rbac import require_permission
from app.models.user import User
from app.services.dimension_service import DimensionService
from app.models.data_quality_rule import DataQualityDimension

router = APIRouter(prefix="/dimensions", tags=["Data Quality Dimensions"])


@router.get("", summary="Get all dimension configurations")
async def get_all_dimensions(
    current_user: User = Depends(get_current_user_from_token),
    _: None = Depends(require_permission("data_quality:view")),
):
    """Get configurations for all data quality dimensions"""
    dimensions = DimensionService.get_all_dimensions()
    return {
        "dimensions": [
            {
                "name": dim.upper(),
                "description": config.description,
                "examples": config.examples,
                "common_rule_types": config.common_rule_types,
                "validation_tips": config.validation_tips,
                "related_frameworks": config.related_frameworks,
            }
            for dim, config in dimensions.items()
        ]
    }


@router.get("/{dimension}", summary="Get dimension configuration")
async def get_dimension(
    dimension: str,
    current_user: User = Depends(get_current_user_from_token),
    _: None = Depends(require_permission("data_quality:view")),
):
    """Get configuration for a specific dimension"""
    try:
        dim = DataQualityDimension(dimension.lower())
        config = DimensionService.get_dimension_config(dim)
        return {
            "name": dim.value.upper(),
            "description": config.description,
            "examples": config.examples,
            "common_rule_types": config.common_rule_types,
            "validation_tips": config.validation_tips,
            "related_frameworks": config.related_frameworks,
        }
    except ValueError:
        return {"error": f"Invalid dimension: {dimension}"}, 400


@router.get("/{dimension}/rule-types", summary="Get recommended rule types for dimension")
async def get_rule_types(
    dimension: str,
    current_user: User = Depends(get_current_user_from_token),
    _: None = Depends(require_permission("data_quality:view")),
):
    """Get recommended rule types for a specific dimension"""
    try:
        dim = DataQualityDimension(dimension.lower())
        rule_types = DimensionService.get_dimension_rule_types(dim)
        return {"dimension": dim.value, "rule_types": rule_types}
    except ValueError:
        return {"error": f"Invalid dimension: {dimension}"}, 400


@router.get("/{dimension}/tips", summary="Get validation tips for dimension")
async def get_validation_tips(
    dimension: str,
    current_user: User = Depends(get_current_user_from_token),
    _: None = Depends(require_permission("data_quality:view")),
):
    """Get validation tips for a specific dimension"""
    try:
        dim = DataQualityDimension(dimension.lower())
        tips = DimensionService.get_dimension_validation_tips(dim)
        return {"dimension": dim.value, "validation_tips": tips}
    except ValueError:
        return {"error": f"Invalid dimension: {dimension}"}, 400
