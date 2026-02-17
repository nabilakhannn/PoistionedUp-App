# Pattern: FastAPI + Supabase Auth

**Source:** Slice 3 (API: create workflow + status)
**Date:** 2026-02-12

## Pattern

JWT authentication for FastAPI using Supabase Auth.

### Auth Flow
1. Frontend signs in via Supabase Auth SDK -> gets a JWT (access_token)
2. Frontend sends `Authorization: Bearer <token>` on every API call
3. FastAPI extracts the token and calls `admin.auth.get_user(token)`
4. Supabase verifies the JWT signature and returns the user object
5. We extract `user.id` and `user.email` for downstream use

### Key Files
- `app/auth.py` -- `get_current_user` dependency
- `app/deps.py` -- `get_admin_client` factory

### Gotchas Discovered

1. **Python 3.9 compatibility:** Don't use `str | None` syntax. Use `Optional[str]` from `typing` or `from __future__ import annotations`.

2. **`maybe_single()` returns `None`, not an object with `.data = None`:**
   ```python
   # WRONG -- crashes with AttributeError
   resp = table.select("*").eq("id", x).maybe_single().execute()
   if not resp.data:  # AttributeError: NoneType has no attribute 'data'

   # RIGHT -- use .execute() and check .data list
   resp = table.select("*").eq("id", x).execute()
   if not resp.data:
       raise HTTPException(404)
   row = resp.data[0]
   ```

3. **`.env` file location:** Pydantic Settings looks for `.env` relative to CWD. When running from `apps/api/`, the project root `.env` isn't found. Fix: resolve the path explicitly.
   ```python
   _PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
   _ENV_FILE = _PROJECT_ROOT / ".env"
   model_config = {"env_file": str(_ENV_FILE), ...}
   ```

4. **Extra env vars:** `.env` may contain vars not in the Settings model (e.g. `NEXT_PUBLIC_*`). Set `"extra": "ignore"` in `model_config` to avoid validation errors.

5. **Service role vs anon key:** Backend uses `service_role_key` (bypasses RLS) for all DB operations. The auth middleware validates the user's JWT, then the backend scopes queries by `user_id` itself. RLS acts as a safety net against code bugs.

### Test Pattern
- Create test users via `admin.auth.admin.create_user()`
- Sign in to get JWT via `anon_client.auth.sign_in_with_password()`
- Send requests with `httpx` to the running server
- Clean up test users in fixture teardown
