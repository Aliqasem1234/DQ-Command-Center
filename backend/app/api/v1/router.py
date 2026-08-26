from fastapi import APIRouter
from app.api.v1 import auth
from app.api.v1 import departments
from app.api.v1 import users
from app.api.v1 import roles
from app.api.v1 import permissions
from app.api.v1 import audit
from app.api.v1 import dashboard
from app.api.v1 import data_quality
from app.api.v1 import data_hierarchy_routes
from app.api.v1 import dimensions
from app.api.v1 import results
from app.api.v1 import governance
from app.api.v1 import dataset_files

router = APIRouter(prefix="/api/v1")

router.include_router(auth.router, tags=["Authentication"])
router.include_router(departments.router, tags=["Departments"])
router.include_router(users.router, tags=["Users"])
router.include_router(roles.router, tags=["Roles"])
router.include_router(permissions.router, tags=["Permissions"])
router.include_router(audit.router, tags=["Audit"])
router.include_router(dashboard.router, tags=["Dashboard"])
router.include_router(data_quality.router, tags=["Data Quality"])
router.include_router(data_hierarchy_routes.router, tags=["Data Hierarchy"])
router.include_router(dimensions.router, tags=["Dimensions"])
router.include_router(results.router, tags=["Results Reporting"])
router.include_router(governance.router, tags=["Data Governance"])
router.include_router(dataset_files.router, tags=["Dataset Files"])
