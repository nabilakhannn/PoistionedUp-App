# Quick Reference Guide

## How to Start the App

```bash
# From project root
./dev.sh
```

This starts both servers:
- Frontend: http://localhost:3000
- Backend: http://localhost:8000

## Test Credentials

**Email:** `test@example.com`
**Password:** `testpass123`

## Available Routes

### Auth Pages (Public)
- http://localhost:3000/login
- http://localhost:3000/signup

### Protected Pages (Require Login)
- http://localhost:3000/brand - Brand dashboard
- http://localhost:3000/brand/chat/foundation
- http://localhost:3000/brand/chat/ica
- http://localhost:3000/brand/chat/offer
- http://localhost:3000/brand/chat/brand
- http://localhost:3000/knowledge - Knowledge base
- http://localhost:3000/performance - Performance tracking
- http://localhost:3000/memory - Agent memory
- http://localhost:3000/experiments - Experiments

## Running E2E Tests

```bash
cd apps/web
npm run test:e2e

# Or with UI mode
npx playwright test --ui
```

## Common Issues & Quick Fixes

### Issue: "Cannot reach the server"
**Fix:** Check token expiry. Auto-refresh should handle this, but if not:
1. Sign out
2. Sign in again
3. Should get fresh token

### Issue: CORS blocking requests
**Fix:** Browser cache issue
1. Hard refresh: Cmd+Shift+R (Mac) / Ctrl+Shift+R (Windows)
2. OR clear browser cache
3. OR use Incognito/Private mode

### Issue: Backend not running
**Fix:** Restart backend
```bash
lsof -ti:8000 | xargs kill -9
cd apps/api
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
```

### Issue: Frontend not running
**Fix:** Restart frontend
```bash
pkill -f "next dev"
cd apps/web
npm run dev &
```

### Issue: Both servers need restart
**Fix:** Use dev.sh
```bash
./dev.sh
```

## Debugging Checklist

When auth isn't working:

1. ✅ Check if backend is running: `curl http://localhost:8000/health`
2. ✅ Check if frontend is running: `curl http://localhost:3000`
3. ✅ Check token expiry in browser console:
   ```javascript
   // Open browser console (F12)
   const supabase = window.supabase || ...
   supabase.auth.getSession().then(({data}) => {
     console.log('Expires:', data.session?.expires_at);
     console.log('Current:', Date.now() / 1000);
     console.log('Valid:', data.session?.expires_at > Date.now() / 1000);
   });
   ```
4. ✅ Check CORS headers:
   ```bash
   curl -i http://localhost:8000/health -H "Origin: http://localhost:3000"
   # Should see: access-control-allow-origin: http://localhost:3000
   ```
5. ✅ Check backend logs for auth errors:
   ```bash
   # Look for: [auth] Token validation failed
   ```
6. ✅ Clear browser cache and try in Incognito mode
7. ✅ Sign out and sign in with fresh session

## File Locations

### Frontend Auth Files
```
apps/web/src/
├── lib/supabase/
│   ├── client.ts          # Browser client (singleton)
│   ├── server.ts          # Server client (for SSR)
│   └── middleware.ts      # Session refresh + redirects
├── middleware.ts          # Next.js middleware entry
├── lib/api.ts             # API client with auto-refresh
└── app/
    ├── login/page.tsx     # Login page
    ├── signup/page.tsx    # Signup page
    └── nav-bar.tsx        # Navigation with sign out
```

### Backend Auth Files
```
apps/api/app/
├── auth.py                # JWT validation (returns 401)
├── deps.py                # Admin client
├── config.py              # CORS settings
└── main.py                # CORS middleware
```

### Database
```
infra/supabase/migrations/
└── 007_auto_profile.sql   # Auto-create profile on signup
```

### Tests
```
apps/web/
├── tests/auth.spec.ts     # E2E tests (4 tests)
├── playwright.config.ts   # Test config
└── E2E_SETUP.md          # Setup guide
```

### Documentation
```
docs/
├── compound/patterns/
│   └── slice-15-supabase-auth.md    # Complete pattern doc
├── compound/reviews/
│   └── slice-15-auth-review.md      # Slice review
└── auth-setup-session/              # This session log
    ├── 01-problem-statement.md
    ├── 02-implementation-timeline.md
    ├── 03-errors-and-fixes.md
    ├── 04-quick-reference.md         # This file
    └── 05-final-summary.md
```

## Environment Variables

### Required in .env
```bash
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://qvlknqevyixpanqiklte.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGc...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...

# API
NEXT_PUBLIC_API_URL=http://localhost:8000

# OpenAI
OPENAI_API_KEY=sk-proj-...
```

## Key Commands

```bash
# Start both servers
./dev.sh

# Run E2E tests
cd apps/web && npm run test:e2e

# Check backend health
curl http://localhost:8000/health

# Check CORS
curl -i http://localhost:8000/health -H "Origin: http://localhost:3000"

# Kill port 8000
lsof -ti:8000 | xargs kill -9

# Kill Next.js
pkill -f "next dev"
```

## Supabase Dashboard

**Project:** qvlknqevyixpanqiklte
**URL:** https://supabase.com/dashboard/project/qvlknqevyixpanqiklte

### Useful Pages:
- **Authentication → Users** - View all users
- **Authentication → Policies** - RLS policies
- **Table Editor → profiles** - User profiles
- **Project Settings → Auth** - JWT expiry settings

### Extending JWT Expiry:
1. Go to Project Settings → Auth
2. Find "JWT Expiry"
3. Change from 3600 (1 hour) to 86400 (24 hours)
4. Save

## Next Steps

1. Fix browser cache (clear cache or use incognito)
2. Verify auth works end-to-end
3. Optional: Extend JWT expiry in Supabase Dashboard
4. Continue with Slice 16 (YouTube Auto-Import)
