"""In-memory sliding window rate limiter middleware.

Provides per-IP rate limiting with tiered limits based on endpoint category:
  - LLM endpoints (chat, strategist, research, workflows): strict limits
  - Agent bridge endpoints: moderate limits (server-to-server)
  - General endpoints: generous limits

Design:
  - Uses a sliding window counter per IP address
  - Thread-safe via a lock
  - Periodic cleanup of expired entries to prevent memory growth
  - Returns 429 with Retry-After header on limit exceeded
  - No external dependencies (Redis can be swapped in later)

To swap to Redis-backed in production:
  Replace _RateLimitStore with a Redis-backed implementation
  that uses INCR + EXPIRE for atomic sliding windows.
"""

import logging
import time
import threading
from collections import defaultdict
from typing import Dict, List, Tuple

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("app.middleware.rate_limit")

# ── Rate limit tiers ─────────────────────────────────────────

# (max_requests, window_seconds)
TIER_LLM: Tuple[int, int] = (30, 60)        # 30 req/min for LLM-heavy endpoints
TIER_ORCHESTRATOR: Tuple[int, int] = (5, 60) # 5 req/min for orchestrator (spawns multiple LLM pipelines)
TIER_AGENT: Tuple[int, int] = (120, 60)      # 120 req/min for agent bridge
TIER_WRITE: Tuple[int, int] = (60, 60)       # 60 req/min for write operations
TIER_READ: Tuple[int, int] = (200, 60)       # 200 req/min for general reads
TIER_AUTH: Tuple[int, int] = (10, 60)        # 10 req/min for auth endpoints (brute force protection)

# Prefix → tier mapping (checked in order, first match wins)
_ROUTE_TIERS: List[Tuple[str, Tuple[int, int]]] = [
    # Auth (strictest — brute force protection)
    ("/auth/", TIER_AUTH),
    ("/login", TIER_AUTH),
    ("/signup", TIER_AUTH),

    # LLM-heavy endpoints
    ("/brand/chat", TIER_LLM),
    ("/brand/suggest", TIER_LLM),
    ("/brand/strategist/chat", TIER_LLM),
    ("/brands/", TIER_LLM),   # research/run endpoints hit LLM
    ("/content-chat/", TIER_LLM),
    ("/repurpose", TIER_LLM),
    ("/advisor/suggestions", TIER_LLM),
    ("/competitors/full-analysis", TIER_LLM),
    ("/competitors", TIER_WRITE),
    ("/qa/reviews", TIER_READ),
    ("/qa/stats", TIER_READ),
    ("/qa/review", TIER_LLM),
    ("/workflows", TIER_LLM),

    # Orchestrator (strictest LLM tier — spawns multiple pipelines per call)
    ("/orchestrator/pulse", TIER_ORCHESTRATOR),
    ("/orchestrator/trigger", TIER_ORCHESTRATOR),
    ("/orchestrator/execute", TIER_ORCHESTRATOR),
    ("/orchestrator/status", TIER_READ),
    ("/orchestrator/schedules", TIER_READ),

    # Gateway (message relay hits LLM on remote agent, reads are moderate)
    ("/gateway/message", TIER_LLM),
    ("/gateway/", TIER_WRITE),

    # Agent bridge (server-to-server)
    ("/agent-api/", TIER_AGENT),

    # Mission control (moderate writes)
    ("/mission-control/", TIER_WRITE),

    # Everything else
]

# Paths that skip rate limiting entirely
_EXEMPT_PATHS = frozenset({"/", "/health", "/docs", "/openapi.json", "/favicon.ico"})


def _get_tier(path: str, method: str) -> Tuple[int, int]:
    """Determine the rate limit tier for a request."""
    for prefix, tier in _ROUTE_TIERS:
        if path.startswith(prefix):
            # The research /run endpoint hits LLM, but GET endpoints are reads
            if "research" in path and method == "GET":
                return TIER_READ
            # Competitor /analyze and /refresh hit LLM — stricter tier
            if path.startswith("/competitors") and (
                path.endswith("/analyze") or path.endswith("/refresh")
            ):
                return TIER_LLM
            return tier
    return TIER_READ


# ── In-memory store ──────────────────────────────────────────


class _RateLimitStore:
    """Thread-safe in-memory sliding window rate limit store.

    Stores a list of request timestamps per key (IP address).
    Periodically prunes expired entries to prevent unbounded memory growth.
    """

    def __init__(self):
        self._data: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # prune every 5 minutes

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> Tuple[bool, int]:
        """Check if a request is allowed under the rate limit.

        Returns (allowed: bool, remaining: int).
        """
        now = time.time()
        cutoff = now - window_seconds

        with self._lock:
            # Prune old timestamps for this key
            timestamps = self._data[key]
            self._data[key] = [ts for ts in timestamps if ts > cutoff]
            timestamps = self._data[key]

            if len(timestamps) >= max_requests:
                # Calculate when the oldest request in the window expires
                return False, 0

            timestamps.append(now)
            remaining = max_requests - len(timestamps)

            # Periodic global cleanup
            if now - self._last_cleanup > self._cleanup_interval:
                self._cleanup(cutoff)
                self._last_cleanup = now

            return True, remaining

    def _cleanup(self, cutoff: float) -> None:
        """Remove keys with no recent requests (already holding the lock)."""
        empty_keys = [k for k, v in self._data.items() if not v or all(ts <= cutoff for ts in v)]
        for k in empty_keys:
            del self._data[k]
        if empty_keys:
            logger.debug("Rate limit store cleanup: removed %d stale keys", len(empty_keys))


_store = _RateLimitStore()


# ── Middleware ────────────────────────────────────────────────


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-IP rate limiting with tiered limits by endpoint category.

    Adds headers to every response:
      X-RateLimit-Limit: max requests in window
      X-RateLimit-Remaining: requests left
      X-RateLimit-Reset: window duration in seconds

    Returns 429 Too Many Requests when limit exceeded.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip exempt paths
        if path in _EXEMPT_PATHS:
            return await call_next(request)

        # Skip OPTIONS (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Get client IP (respect X-Forwarded-For for reverse proxies)
        client_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        if not client_ip:
            client_ip = request.client.host if request.client else "unknown"

        max_requests, window_seconds = _get_tier(path, request.method)
        rate_key = f"{client_ip}:{path.split('/')[1]}"  # Group by IP + first path segment

        allowed, remaining = _store.is_allowed(rate_key, max_requests, window_seconds)

        if not allowed:
            logger.warning(
                "Rate limit exceeded: ip=%s path=%s limit=%d/%ds",
                client_ip, path, max_requests, window_seconds,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "type": "error",
                    "error": {
                        "type": "rate_limit_exceeded",
                        "message": "Too many requests. Please slow down.",
                    },
                },
                headers={
                    "Retry-After": str(window_seconds),
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(window_seconds),
                },
            )

        response = await call_next(request)

        # Add rate limit headers to successful responses
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(window_seconds)

        return response
