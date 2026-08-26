import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.api.v1.router import router as v1_router
from app.middleware.security import SecurityHeadersMiddleware
from app.core.limiter import limiter
from app.core.seed_secure import secure_initialize

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.DEBUG),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} in {settings.ENVIRONMENT} mode")
    try:
        await secure_initialize()
    except Exception as e:
        logger.error(f"Failed to initialize system: {e}", exc_info=True)
    
    logger.info(f"Swagger docs available at /docs")
    logger.info(f"OpenAPI spec available at /openapi.json")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    description="""
    Enterprise Data Quality & Data Governance Platform.
    
    ## Authentication
    - Use `/api/v1/auth/login` to get access and refresh tokens
    - Access tokens expire in 15 minutes
    - Use `/api/v1/auth/refresh` to get new tokens
    - All protected endpoints require `Authorization: Bearer <token>` header
    
    ## Rate Limiting
    - Auth endpoints have rate limiting to prevent brute force attacks
      (enforced by this API directly, and again at the nginx layer)
    - Login: 10 requests/minute
    - Register: 5 requests/minute
    - Forgot password: 3 requests/minute
    - General API: 120 requests/minute (safety net)
    """,
    version="1.0.0",
    # API docs expose the full route/schema surface - only serve them
    # outside production.
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    openapi_url="/openapi.json" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# Security headers
app.add_middleware(SecurityHeadersMiddleware)

# Rate limiter (shared instance in app.core.limiter so route modules can
# apply per-endpoint limits via @limiter.limit(...))
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Include routers
app.include_router(v1_router)


# Health check
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred"},
    )
