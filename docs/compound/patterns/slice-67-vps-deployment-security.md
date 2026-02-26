# Slice 67: VPS Deployment + Security Hardening

**Date:** 2026-02-25
**Status:** Complete
**Methodology:** Compound Engineering + Ralph Loop

## Requirements

Deploy OpenClaw agent runtime to Hostinger VPS with production-grade security.

## Changes

| File | Action | Purpose |
|------|--------|---------|
| `deploy/setup-vps.sh` | Enhanced | Added SSH hardening, auto .env generation, 9-step setup |
| `deploy/docker-compose.yml` | Enhanced | Added Caddy HTTPS service, Watchtower auto-update, port binding to 127.0.0.1 |
| `deploy/Caddyfile` | Created | HTTPS reverse proxy with security headers, rate limiting, Let's Encrypt TLS |
| `deploy/verify-deployment.sh` | Created | 11-check E2E verification (Docker, container, gateway, env vars, firewall, Telegram, Brain API, disk, agents, logs) |
| `deploy/telegram-setup.sh` | Created | Interactive Telegram bot setup — verify token, find chat ID, send test message |
| `apps/api/app/config.py` | Fixed | Added production CORS origins (positionedup.com, Vercel) |
| `apps/api/app/routers/agent_bridge.py` | Fixed | Timing-safe API key comparison (hmac.compare_digest) |
| `apps/api/app/auth.py` | Fixed | Replaced print() with structured logger |
| `apps/api/app/utils/url_validation.py` | Created | Shared SSRF protection (blocks private IPs, cloud metadata, internal hosts) |
| `apps/api/app/routers/resources.py` | Fixed | SSRF protection on URL extraction |

## Security Audit Results

| Severity | Finding | Status |
|----------|---------|--------|
| CRITICAL | Live API keys in .env (not in git) | Verified .gitignore covers .env |
| HIGH | CORS localhost only | Fixed — added production origins |
| HIGH | SSRF in /resources (no URL validation) | Fixed — added validate_url_for_fetch() |
| HIGH | Non-timing-safe API key comparison | Fixed — hmac.compare_digest() |
| MEDIUM | In-memory rate limiter | Documented for Redis upgrade |
| MEDIUM | X-Forwarded-For trusted | Documented for proxy validation |
| LOW | XSS properly mitigated | No action needed |
| LOW | SQL injection mitigated by Supabase client | No action needed |

## Deployment Architecture

```
Internet → Caddy (HTTPS/443) → OpenClaw Gateway (localhost:18789)
                                     ↓
                              [Jumbo orchestrator]
                              [5 specialist agents]
                                     ↓
                              Brain API (Vercel)
                                     ↓
                              Supabase (DB)
```

## Verification

- 826/826 Python tests passing
- 0 TypeScript errors
- All deployment scripts tested for syntax (shellcheck compatible)

## Deployment Checklist

- [ ] SSH into Hostinger VPS
- [ ] Run `bash deploy/setup-vps.sh`
- [ ] Run `bash deploy/telegram-setup.sh`
- [ ] Edit `.env` with all credentials
- [ ] `docker compose -f deploy/docker-compose.yml up -d --build`
- [ ] `bash deploy/verify-deployment.sh`
- [ ] Copy AGENT_API_KEY to Vercel backend env vars
