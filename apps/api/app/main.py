import app.openai_compat_patch  # noqa: F401  -- must be first to patch before any OpenAI usage

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.routers import brand, collections, experiments, memory, oauth, performance, research, resources, schedule, usage, workflows

# ── Structured logging setup ─────────────────────────────

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.DEBUG),
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("app")


# ── Request logging middleware ────────────────────────────

_REDACT_HEADERS = {"authorization", "cookie", "x-api-key"}
_REDACT_PARAMS = {"code", "token", "access_token", "refresh_token", "state"}


def _redact_query(url_path: str) -> str:
    """Strip sensitive query parameters from logged paths."""
    if "?" not in url_path:
        return url_path
    base, qs = url_path.split("?", 1)
    pairs = qs.split("&")
    safe = []
    for pair in pairs:
        key = pair.split("=", 1)[0].lower()
        if key in _REDACT_PARAMS:
            safe.append(f"{key}=***")
        else:
            safe.append(pair)
    return f"{base}?{'&'.join(safe)}"


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with method, path, status, and duration.

    Redacts sensitive data:
      - Authorization / cookie headers are never logged
      - Query params with token/code/state are masked
    """

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        start = time.time()

        # Add request_id to request state for downstream use
        request.state.request_id = request_id

        response = await call_next(request)

        duration_ms = round((time.time() - start) * 1000, 1)
        path = _redact_query(str(request.url.path) + ("?" + str(request.url.query) if request.url.query else ""))

        # Skip noisy health/docs checks from logs
        if request.url.path not in ("/health", "/docs", "/openapi.json", "/favicon.ico"):
            logger.info(
                "req=%s %s %s -> %s (%sms)",
                request_id,
                request.method,
                path,
                response.status_code,
                duration_ms,
            )

        response.headers["X-Request-ID"] = request_id
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("PositionedUp API starting up")
    yield
    logger.info("PositionedUp API shutting down")


app = FastAPI(
    title="PositionedUp API",
    version="0.1.0",
    lifespan=lifespan,
)

# Middleware order matters: request logging runs before CORS
app.add_middleware(RequestLoggingMiddleware)

app.include_router(workflows.router)
app.include_router(resources.router)
app.include_router(brand.router)
app.include_router(collections.router)
app.include_router(performance.router)
app.include_router(memory.router)
app.include_router(experiments.router)
app.include_router(research.router)
app.include_router(usage.router)
app.include_router(schedule.router)
app.include_router(oauth.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "app": "PositionedUp API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
async def health_check():
    """Health check with optional DB connectivity test."""
    health = {
        "status": "ok",
        "version": "0.1.0",
    }

    # Quick DB check: try to query the profiles table count
    try:
        from app.deps import get_admin_client
        admin = get_admin_client()
        admin.table("profiles").select("user_id", count="exact").limit(0).execute()
        health["db"] = "connected"
    except Exception as e:
        health["db"] = "error"
        health["db_error"] = str(e)[:200]
        health["status"] = "degraded"

    return health
