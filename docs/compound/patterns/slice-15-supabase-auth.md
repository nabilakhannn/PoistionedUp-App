# Slice 15: Supabase Auth (Email + Password)

## Pattern: Cookie-Based Auth with @supabase/ssr

### Problem
The app had 13 pages, a backend with JWT validation, and RLS on every table — but no
way to actually log in. The frontend read a token from `localStorage` that nothing set.

### Solution: @supabase/ssr + Next.js Middleware

1. **Browser client** (`createBrowserClient`) — used by all `"use client"` pages
2. **Server client** (`createServerClient`) — used by Server Components / Route Handlers
3. **Middleware client** — refreshes session cookies on every request, redirects to `/login`
   if unauthenticated, redirects away from `/login` if already authenticated

### Key Architecture Decisions

- **`@supabase/ssr` over `@supabase/auth-helpers-nextjs`**: Auth helpers are deprecated.
  `@supabase/ssr` is the modern replacement, uses cookie-based sessions (not localStorage).
- **Cookie-based > localStorage**: More secure, works with SSR/middleware, auto-chunked
  if JWT > 4KB.
- **Middleware handles all redirects**: No auth checks in individual pages. Middleware
  runs before every page load, so unauthenticated users never see protected content.
- **Backend unchanged**: `app/auth.py` already validates Supabase JWTs via
  `admin.auth.get_user(token)`. No backend changes needed.
- **Auto-profile trigger**: Postgres trigger on `auth.users` INSERT creates a `profiles`
  row so new users don't get 404s on first API call.

### File Layout

```
apps/web/src/
├── lib/supabase/
│   ├── client.ts      # createBrowserClient (for "use client" pages)
│   ├── server.ts      # createServerClient (for Server Components)
│   └── middleware.ts   # updateSession() — refresh + redirects
├── middleware.ts       # Next.js entry — calls updateSession()
└── app/
    ├── login/page.tsx  # Email + password sign-in
    ├── signup/page.tsx # Email + password sign-up
    └── nav-bar.tsx     # Sign-out button (hidden on login/signup)

infra/supabase/migrations/
└── 007_auto_profile.sql  # Trigger: auth.users INSERT → profiles row
```

### Gotchas

1. **Do NOT add code between `createServerClient` and `supabase.auth.getUser()`** in
   middleware. Random logouts result.
2. **`cookies()` is async** in Next.js 15 — must `await cookies()` in server client.
3. **Server Components can't set cookies** — `setAll` needs a try/catch in server.ts.
4. **Middleware matcher** must exclude `_next/static`, `_next/image`, `favicon.ico`, and
   image file extensions, or static assets will trigger auth redirects.
5. **NavBar hides on `/login` and `/signup`** — check `usePathname()` to avoid showing
   sign-out on auth pages.
6. **Trigger already exists error** — use `DROP TRIGGER IF EXISTS` before `CREATE TRIGGER`
   when re-running migration.
7. **`@supabase/ssr` stores auth in cookies, not localStorage** — the API client must use
   `supabase.auth.getSession()` to get the access token, not `localStorage.getItem()`.

### API Client Token Flow

```typescript
// OLD (broken — nothing set this):
const token = localStorage.getItem("supabase_token");

// NEW (reads from cookie-based session):
const supabase = createClient();
const { data } = await supabase.auth.getSession();
const token = data.session?.access_token ?? "";
```

### Critical: Token Expiry & Auto-Refresh

**Problem:** Supabase JWTs expire after 1 hour (default `jwt_expiry = 3600`). If the frontend
doesn't refresh the token before it expires, API calls fail with 401.

**Solution:** Auto-refresh in the API client ([apps/web/src/lib/api.ts](apps/web/src/lib/api.ts)):

```typescript
// Before every API call:
const { data } = await supabase.auth.getSession();
const expiresAt = data.session?.expires_at;

// If token expires in < 5 minutes, refresh it
if (expiresAt && expiresAt < Date.now() / 1000 + 300) {
  const { data: refreshData, error } = await supabase.auth.refreshSession();
  if (error) {
    await supabase.auth.signOut();
    window.location.href = "/login";
    throw new Error("Session expired");
  }
  token = refreshData.session?.access_token ?? token;
}
```

**Also recommended:** Extend token lifetime in Supabase Dashboard → Project Settings → Auth → JWT Expiry
(e.g., `86400` = 24 hours).

### Backend Error Handling: 401 vs 500

**Problem:** When a token is expired/invalid, the backend was returning 500 Internal Server Error
instead of 401 Unauthorized. Frontend couldn't distinguish between auth failures and real server errors.

**Solution:** Catch Supabase exceptions in [apps/api/app/auth.py](apps/api/app/auth.py) and always
return 401:

```python
try:
    resp = admin.auth.get_user(token)
except Exception as e:
    # Log the actual error for debugging but return 401 to client
    print(f"[auth] Token validation failed: {type(e).__name__}: {e}")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
    )
```

This allows the frontend to detect auth failures and redirect to `/login`, rather than showing
a generic "Cannot reach the server" error.

### Post-Login Redirect: window.location.href vs router.push()

**Problem:** Using Next.js `router.push("/brand")` after login sometimes resulted in the session
cookie not being set on the first request to `/brand`, causing a redirect loop back to `/login`.

**Solution:** Use `window.location.href = "/brand"` instead of `router.push()`. This triggers a
full page reload, ensuring all cookies propagate correctly before the redirect.

```typescript
// apps/web/src/app/login/page.tsx
if (data.session) {
  window.location.href = "/brand";  // ✅ Full reload
} else {
  setError("Login succeeded but no session created. Please try again.");
  setLoading(false);
}
```

### Singleton Pattern for Browser Client

**Problem:** Creating a new Supabase client on every `createClient()` call can lead to session
inconsistencies across different components.

**Solution:** Use a singleton pattern in [apps/web/src/lib/supabase/client.ts](apps/web/src/lib/supabase/client.ts):

```typescript
let client: ReturnType<typeof createBrowserClient> | null = null;

export function createClient() {
  if (!client) {
    client = createBrowserClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    );
  }
  return client;
}
```

This ensures all components share the same Supabase instance and session state.

### E2E Testing

**Files:**
- [apps/web/tests/auth.spec.ts](apps/web/tests/auth.spec.ts) - Playwright tests
- [apps/web/playwright.config.ts](apps/web/playwright.config.ts) - Config
- [apps/web/E2E_SETUP.md](apps/web/E2E_SETUP.md) - Setup instructions

**Test Coverage:**
1. Full auth flow (login → protected page → sign out)
2. Invalid credentials rejection
3. Unauthenticated redirect to login
4. Authenticated redirect away from login

**Setup:**
```bash
cd apps/web
npm i -D @playwright/test
npx playwright install
npm run test:e2e
```

### Testing Checklist

- [x] `localhost:3000` → redirects to `/login`
- [x] Sign up → lands on `/brand`
- [x] API calls include `Authorization: Bearer <real JWT>`
- [x] Supabase Dashboard → Auth → Users shows new user
- [x] Supabase Dashboard → Table Editor → profiles shows auto-created row
- [x] Sign out → redirects to `/login`
- [x] Visiting `/brand` while logged out → redirects to `/login`
- [x] Visiting `/login` while logged in → redirects to `/brand`
- [x] Token auto-refreshes before expiry (< 5 min remaining)
- [x] Backend returns 401 (not 500) for expired tokens
- [x] E2E tests pass
