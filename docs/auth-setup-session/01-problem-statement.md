# Problem Statement

## Initial Issue
User requested: "set up Supabase Auth"

## Context
- App had 13 pages built
- Backend had JWT validation configured
- Database had RLS (Row Level Security) enabled
- **But no way to actually log in!**
- Frontend tried to read token from localStorage that nothing ever set
- Every API call failed with "Cannot reach the server"

## User Requirements
- Email + password authentication
- Cookie-based sessions (not localStorage)
- Auto-refresh tokens before expiry
- Proper error handling (401 not 500)
- E2E tests to prevent breakage
- Use Compound Engineering methodology throughout
- UI/UX should be aesthetic and intuitive (deferred until auth is stable)

## Initial State
```
Frontend: Next.js 14+ (App Router)
Backend: FastAPI with Supabase JWT validation
Database: Supabase Postgres with RLS
Auth: None! ❌
```

## Goal
Complete, production-ready authentication system with:
- Sign up / Sign in / Sign out
- Session persistence
- Token auto-refresh
- Backend 401 error handling
- E2E test coverage
- Full documentation
