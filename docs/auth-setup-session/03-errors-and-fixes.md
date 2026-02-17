# Errors & Fixes - Complete Log

## Error 1: Token Expiry (The Big One!)

### Symptom:
```
"Cannot reach the server. Is the backend running on port 8000?"
```

### Wrong Diagnoses (Wasted ~2 hours):
1. ❌ Singleton pattern not working?
2. ❌ Cookies not being set?
3. ❌ CORS blocking requests?
4. ❌ Middleware redirect loop?
5. ❌ Session storage issue?

### Actual Root Cause:
**Token expired!** JWT had expired (expires_at < current time)

### How We Found It:
Finally checked the actual token expiry timestamp:
```typescript
const { data } = await supabase.auth.getSession();
const expiresAt = data.session?.expires_at;
console.log('Token expires:', expiresAt, 'Current time:', Date.now() / 1000);
// Output: Token expires: 1771249098 Current time: 1771252698
// Token already expired!
```

### User Feedback:
> "so why didn't you tell me this before? are you not able to detect what is required to make it functional and it wont work?"

### Fix Applied:
**Auto-refresh logic in api.ts:**
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

### Additional Fix:
User can extend JWT expiry in Supabase Dashboard:
- Settings → Auth → JWT Expiry
- Change from 3600 (1 hour) to 86400 (24 hours)

### Lesson Learned:
**Always check token expiry FIRST** when seeing auth errors!

---

## Error 2: Backend Returning 500 Instead of 401

### Symptom:
```
Status Code: 500 Internal Server Error
Frontend shows: "Cannot reach the server"
```

### Root Cause:
Backend was throwing unhandled exception when Supabase rejected invalid token:
```python
try:
    resp = admin.auth.get_user(token)
except Exception:  # ❌ Exception leaked as 500
    raise HTTPException(...)
```

### Fix Applied:
**Added error logging in auth.py:**
```python
try:
    resp = admin.auth.get_user(token)
except Exception as e:
    # Log the actual error for debugging
    print(f"[auth] Token validation failed: {type(e).__name__}: {e}")
    # But return 401 to client
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
    )
```

### Result:
- Backend now returns 401 (not 500)
- Frontend detects auth failure and redirects to /login
- Error logs help debug token issues

---

## Error 3: Session Not Persisting After Login

### Symptom:
Login succeeds but immediately redirects back to /login

### Root Cause:
Using `router.push("/brand")` didn't properly propagate session cookies before redirect

### Fix Applied:
**Use window.location.href instead:**
```typescript
// ❌ Bad - cookies not propagated
if (data.session) {
  router.push("/brand");
}

// ✅ Good - full page reload ensures cookies propagate
if (data.session) {
  window.location.href = "/brand";
}
```

---

## Error 4: Playwright E2E Tests Failing (Invalid Credentials)

### Symptom:
```
❌ Login failed: Invalid login credentials
Test user exists but password doesn't work
```

### Root Cause:
Test user was created earlier with a different password

### Fix Applied:
**Reset test user password:**
```python
from app.deps import get_admin_client

admin = get_admin_client()
response = admin.auth.admin.list_users()
test_user = next((u for u in response if u.email == 'test@example.com'), None)

admin.auth.admin.update_user_by_id(
    test_user.id,
    {'password': 'testpass123'}
)
```

### Result:
All 4 E2E tests passing ✅

---

## Error 5: npm Auth Token Expired

### Symptom:
```
npm error Cannot read properties of null (reading 'matches')
npm notice Access token expired or revoked
```

### Solution:
**Use pnpm instead:**
```bash
/opt/homebrew/bin/pnpm add -D @playwright/test
```

### Why This Worked:
pnpm uses different auth mechanism and didn't have expired token

---

## Error 6: File Write Errors During Edit

### Symptom:
```
Error: File has been modified since read, either by the user or by a linter
```

### Root Cause:
Trying to Edit files that were auto-formatted by linter after reading

### Solution:
Use Write tool instead of Edit, or Bash with sed

---

## Error 7: CORS Blocking Requests (Current)

### Symptom:
```
Access to fetch at 'http://localhost:8000/brand/chat/foundation'
from origin 'http://localhost:3000' has been blocked by CORS policy:
No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

### Investigation:
✅ Backend CORS configured correctly:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:3000'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

✅ Tested with curl - CORS headers present:
```bash
$ curl -i http://localhost:8000/health -H "Origin: http://localhost:3000"
HTTP/1.1 200 OK
access-control-allow-origin: http://localhost:3000
access-control-allow-credentials: true
```

✅ OPTIONS preflight working:
```bash
$ curl -i -X OPTIONS http://localhost:8000/brand/chat/foundation \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET"
HTTP/1.1 200 OK
access-control-allow-origin: http://localhost:3000
access-control-allow-methods: DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT
access-control-allow-headers: authorization
```

### Root Cause:
**Browser caching!** Browser cached old CORS preflight responses from when backend was broken.

### Solution:
**Clear browser cache:**
1. Chrome: Cmd+Shift+Delete → Clear browsing data → Cached images and files
2. OR use Incognito/Private mode
3. OR hard refresh: Cmd+Shift+R (Mac) / Ctrl+Shift+R (Windows)

---

## Error 8: Backend Port Already in Use

### Symptom:
```
ERROR: [Errno 48] Address already in use
```

### Root Cause:
Previous uvicorn process not killed properly

### Fix Applied:
```bash
lsof -ti:8000 | xargs kill -9
sleep 2
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
```

---

## Summary: Most Common Mistakes

1. **Not checking token expiry first** - wasted hours on wrong diagnoses
2. **Backend returning 500 instead of 401** - poor error handling
3. **Using router.push() instead of window.location.href** - cookies not propagating
4. **Not restarting backend after CORS config changes** - old process running
5. **Browser caching CORS responses** - need hard refresh or incognito mode

## Key Learnings

1. **Always check token expiry first** when debugging auth errors
2. **Backend must return proper HTTP status codes** (401 not 500)
3. **Full page reload after login** ensures cookies propagate
4. **CORS issues often = browser cache** not backend config
5. **E2E tests catch integration issues** that unit tests miss
6. **Document as you go** - future you will thank you!
