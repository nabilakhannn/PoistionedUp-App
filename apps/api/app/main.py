import app.openai_compat_patch  # noqa: F401  -- must be first to patch before any OpenAI usage

import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.middleware import RateLimitMiddleware
from app.routers import advisor, agent_bridge, brand, brands, collections, competitors, content_chat, experiments, gateway, goals, inspo, memory, mission_control, notifications, oauth, orchestrator, performance, picker, qa, repurpose, research, resources, schedule, strategist, training, usage, workflows


# ── Structured JSON logging ──────────────────────────────


class StructuredJSONFormatter(logging.Formatter):
    """Outputs log records as single-line JSON for production ingestion.

    Includes timestamp, level, logger name, message, and any extra
    context fields (workflow_id, step_id, user_id, request_id).
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }

        # Attach correlation IDs if present
        for key in ("workflow_id", "step_id", "user_id", "request_id"):
            val = getattr(record, key, None)
            if val:
                log_entry[key] = val

        # Include exception info if present
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


def _setup_logging() -> None:
    """Configure root logger.

    - Production (Vercel / LOG_LEVEL=INFO): structured JSON for log aggregation
    - Local dev (LOG_LEVEL=DEBUG or running outside Vercel): human-readable text
    """
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(level)

    # Clear any existing handlers to avoid duplicate lines
    root.handlers.clear()

    is_production = (
        os.environ.get("VERCEL") == "1"
        or settings.log_level.upper() == "INFO"
    )

    handler = logging.StreamHandler()
    handler.setLevel(level)

    if is_production:
        handler.setFormatter(StructuredJSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(name)s] %(levelname)s %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    root.addHandler(handler)


_setup_logging()
logger = logging.getLogger("app")


# ── Request logging middleware ────────────────────────────

_REDACT_HEADERS = {"authorization", "cookie", "x-api-key", "x-agent-key"}
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
                "%s %s -> %s (%sms)",
                request.method,
                path,
                response.status_code,
                duration_ms,
                extra={"request_id": request_id},
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

# Middleware execution order (bottom added first, so listed in reverse):
#   1. RateLimitMiddleware — reject over-limit requests early
#   2. RequestLoggingMiddleware — log all requests (including 429s)
#   3. CORSMiddleware — handle CORS headers (added below routers)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware)

app.include_router(workflows.router)
app.include_router(resources.router)
app.include_router(brand.router)
app.include_router(brands.router)
app.include_router(collections.router)
app.include_router(performance.router)
app.include_router(memory.router)
app.include_router(experiments.router)
app.include_router(research.router)
app.include_router(usage.router)
app.include_router(schedule.router)
app.include_router(inspo.router)
app.include_router(picker.router)
app.include_router(oauth.router)
app.include_router(advisor.router)
app.include_router(content_chat.router)
app.include_router(strategist.router)
app.include_router(training.router)
app.include_router(mission_control.router)
app.include_router(orchestrator.router)
app.include_router(agent_bridge.router)
app.include_router(gateway.router)
app.include_router(goals.router)
app.include_router(notifications.router)
app.include_router(repurpose.router)
app.include_router(competitors.router)
app.include_router(qa.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
    max_age=3600,
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
        health["status"] = "degraded"
        logger.warning("Health check DB error: %s", str(e)[:200])

    return health


@app.get("/health/llm")
async def llm_health_check():
    """Test OpenAI API connectivity. Returns connection status + latency."""
    import time
    from app.config import settings

    result = {
        "openai_key_set": bool(settings.openai_api_key),
        "openai_key_prefix": settings.openai_api_key[:8] + "..." if settings.openai_api_key else "(empty)",
    }

    if not settings.openai_api_key:
        result["status"] = "error"
        result["detail"] = "OPENAI_API_KEY not configured"
        return result

    try:
        import httpx
        from openai import OpenAI

        start = time.time()
        client = OpenAI(
            api_key=settings.openai_api_key,
            timeout=httpx.Timeout(15.0, connect=5.0),
            max_retries=0,
        )
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say OK"}],
            max_tokens=5,
        )
        elapsed = time.time() - start
        result["status"] = "ok"
        result["response"] = resp.choices[0].message.content
        result["latency_ms"] = round(elapsed * 1000)
        result["model"] = resp.model
    except Exception as e:
        result["status"] = "error"
        result["error_type"] = type(e).__name__
        result["detail"] = str(e)[:500]
        # Dig into the error chain to find the real cause
        cause = e.__cause__
        if cause:
            result["cause_type"] = type(cause).__name__
            result["cause_detail"] = str(cause)[:500]
            inner = cause.__cause__
            if inner:
                result["inner_cause"] = f"{type(inner).__name__}: {str(inner)[:300]}"

    # Also test raw HTTPS connectivity to api.openai.com
    try:
        import httpx as _httpx
        r = _httpx.get("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {settings.openai_api_key}"}, timeout=10.0)
        result["raw_httpx_status"] = r.status_code
        result["raw_httpx_ok"] = r.status_code == 200
    except Exception as raw_err:
        result["raw_httpx_error"] = f"{type(raw_err).__name__}: {str(raw_err)[:300]}"

    return result


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions and return structured error response."""
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.error(
        "Unhandled exception in %s %s: %s",
        request.method,
        request.url.path,
        str(exc),
        exc_info=exc,
        extra={"request_id": request_id},
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "type": "error",
            "error": {
                "type": "internal_server_error",
                "message": "An internal server error occurred",
            },
            "request_id": request_id,
        },
    )
