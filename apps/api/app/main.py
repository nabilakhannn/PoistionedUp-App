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
from app.routers import account_manager, ad_creative, advisor, agent_bridge, analytics_dashboard, brand, brand_chat, brands, campaigns, client_deliverables, client_research, collections, competitors, connectors, content_chat, content_planning, experiments, gateway, goals, hooks, image_gen, inspo, intake, journal, jumbo_hub, knowledge_docs, landing_page, leads, ledger, manus_ai, marketplace, memory, mission_control, newsletter, notifications, oauth, orchestrator, performance, picker, pipeline, pipeline_settings, playbooks, publishing, qa, repurpose, research, resources, schedule, stages, stories, strategist, training, usage, video_content, workflows


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
app.include_router(ad_creative.router)
app.include_router(playbooks.router)
app.include_router(ledger.router)
app.include_router(connectors.router)
app.include_router(publishing.router)
app.include_router(pipeline.router)
app.include_router(pipeline_settings.router)
app.include_router(stages.router)
app.include_router(knowledge_docs.router)
app.include_router(journal.router)
app.include_router(image_gen.router)
app.include_router(landing_page.router)
app.include_router(leads.router)
app.include_router(newsletter.router)
app.include_router(client_research.router)
app.include_router(intake.router)
app.include_router(account_manager.router)
app.include_router(client_deliverables.router)
app.include_router(brand_chat.router)
app.include_router(hooks.router)
app.include_router(content_planning.router)
app.include_router(jumbo_hub.router)
app.include_router(campaigns.router)
app.include_router(video_content.router)
app.include_router(stories.router)
app.include_router(manus_ai.router)
app.include_router(marketplace.router)
app.include_router(analytics_dashboard.router)

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
    """Test OpenAI API connectivity. Returns connection status + latency.

    Never exposes API keys or raw error details containing secrets.
    """
    import time
    from app.config import settings

    result = {
        "openai_key_configured": bool(settings.openai_api_key),
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
        result["latency_ms"] = round(elapsed * 1000)
        result["model"] = resp.model
    except Exception as e:
        result["status"] = "error"
        result["error_type"] = type(e).__name__
        # Sanitize error details — never expose API keys
        detail = str(e)[:500]
        if "sk-" in detail:
            detail = "Connection failed (details redacted for security)"
        result["detail"] = detail

    return result


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions and return structured error response.

    Quota exceptions from the LLM layer are surfaced as HTTP 429 with a
    user-friendly message. All other exceptions return HTTP 500.
    """
    request_id = getattr(request.state, "request_id", "unknown")

    # ── Quota / budget exceptions → 429 Too Many Requests ────────────────
    # Import lazily to avoid circular imports at startup.
    try:
        from worker.graph.llm import DailyTokenCapExceeded, WorkflowBudgetExceeded
        if isinstance(exc, DailyTokenCapExceeded):
            logger.warning(
                "Daily token cap exceeded for request %s %s",
                request.method, request.url.path,
                extra={"request_id": request_id},
            )
            return JSONResponse(
                status_code=429,
                content={
                    "type": "error",
                    "error": {
                        "type": "quota_exceeded",
                        "message": str(exc),
                    },
                    "request_id": request_id,
                },
            )
        if isinstance(exc, WorkflowBudgetExceeded):
            logger.warning(
                "Workflow budget exceeded for request %s %s",
                request.method, request.url.path,
                extra={"request_id": request_id},
            )
            return JSONResponse(
                status_code=429,
                content={
                    "type": "error",
                    "error": {
                        "type": "workflow_budget_exceeded",
                        "message": "This workflow has exceeded its token budget. Start a new workflow.",
                    },
                    "request_id": request_id,
                },
            )
    except ImportError:
        pass

    # ── Generic unhandled exception → 500 ────────────────────────────────
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
