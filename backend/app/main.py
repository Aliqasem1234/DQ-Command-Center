import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
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
    if settings.expose_auth_tokens:
        logger.warning(
            "DEV_EXPOSE_AUTH_TOKENS is on: password-reset and verification tokens are returned "
            "in API responses, so anyone with API access can reset any account. Local use only."
        )
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


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    # Same {"detail": ...} shape as every other API error, so clients have a
    # single error contract (slowapi's default handler answers {"error": ...}).
    response = JSONResponse(
        status_code=429,
        content={"detail": f"Too many requests: rate limit {exc.detail} exceeded. Try again shortly."},
    )
    return request.app.state.limiter._inject_headers(response, request.state.view_rate_limit)


app.add_middleware(SlowAPIMiddleware)

# Include routers
app.include_router(v1_router)


# Health check. Container health checks and nginx's /health use this, so
# it must reflect whether the API can actually serve requests - i.e. reach
# the database - not just whether the process is up.
@app.get("/health", tags=["Health"])
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        await asyncio.wait_for(db.execute(text("SELECT 1")), timeout=3)
        database = "ok"
    except Exception as e:  # noqa: BLE001 - any failure means "not healthy"
        logger.warning(f"Health check: database unreachable ({type(e).__name__})")
        database = "unreachable"
    body = {
        "status": "healthy" if database == "ok" else "unhealthy",
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "database": database,
    }
    return JSONResponse(status_code=200 if database == "ok" else 503, content=body)


# Validation errors keep FastAPI's shape (loc, msg, type, ctx), which the
# frontend maps to readable messages, but never echo the submitted value: a
# too-short password would otherwise come back in the response body.
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [{k: v for k, v in err.items() if k not in ("input", "url")} for err in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(errors)})


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred"},
    )
