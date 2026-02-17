# E2E Testing Setup

## Prerequisites

Your npm auth token expired. Fix it first:

```bash
npm login
```

## Install Playwright

```bash
cd apps/web
npm i -D @playwright/test
npx playwright install
```

## Create Test User

1. Go to your Supabase dashboard: https://supabase.com/dashboard/project/qvlknqevyixpanqiklte
2. Navigate to **Authentication** → **Users**
3. Click **Add user** → **Create new user**
4. Email: `test@example.com`
5. Password: `testpass123`
6. Click **Create user**

## Add Test Credentials

Create `apps/web/.env.test.local`:

```env
TEST_EMAIL=test@example.com
TEST_PASSWORD=testpass123
```

## Run Tests

Make sure both servers are running:

```bash
# From project root
./dev.sh
```

Then in another terminal:

```bash
cd apps/web
npm run test:e2e
```

## What the Tests Cover

1. ✅ **Full auth flow**: login → access protected page → sign out
2. ✅ **Invalid credentials**: shows error message
3. ✅ **Unauthenticated access**: redirects to login
4. ✅ **Already authenticated**: redirects away from login page

## Debugging Failed Tests

If tests fail:

1. Check `playwright-report/index.html` for detailed traces
2. Run with UI mode: `npx playwright test --ui`
3. Run single test: `npx playwright test auth.spec.ts -g "should sign in"`
4. Check backend logs for auth errors (look for `[auth] Token validation failed`)
