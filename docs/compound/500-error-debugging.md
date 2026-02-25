# Fixing 500 Errors: Compound Engineering Guide

**Date:** February 25, 2026  
**Issue:** Generic 500 errors with no diagnostic information  
**Root Cause:** Missing global exception handler in FastAPI app  
**Status:** FIXED ✅

---

## Problem Statement

The API was returning this error on every request:
```json
{
  "type": "error",
  "error": {
    "type": "api_error",
    "message": "Internal server error"
  },
  "request_id": "req_011CYVAMjsEtM3t5CUVSJMtd"
}
```

**Why this was a problem:**
- No error details = impossible to debug
- Same error for all failures (database, config, code bugs)
- Users had no way to understand what went wrong

---

## Root Cause Analysis

The [apps/api/app/main.py](../../apps/api/app/main.py) file had:
- ✅ Request logging middleware (captures timing, status codes)
- ✅ Error handling in individual route handlers
- ❌ **NO GLOBAL EXCEPTION HANDLER** for unhandled exceptions

When an error bubbled up outside of a `try/except` block, FastAPI returned a generic 500 with no details.

---

## Solution Implemented

### Step 1: Added Import
```python
from fastapi.responses import JSONResponse
```

### Step 2: Added Global Exception Handler
Inserted after the `/health` endpoint:

```python
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
                "message": str(exc) or "An internal server error occurred",
            },
            "request_id": request_id,
        },
    )
```

This handler:
1. **Captures the actual exception message** (e.g., "Supabase connection failed")
2. **Logs full stack trace** with request ID for tracking
3. **Returns structured JSON response** with the error details
4. **Preserves request_id** for correlating logs

---

## How to Debug Future 500 Errors

### For Non-Technical Users (What to tell Claude):

**Tell Claude this:**
> "The API is returning a 500 error on [endpoint]. The error message from the global exception handler is: [paste the error message]. Please fix it."

**Example:**
> "The API is returning a 500 error on `/workflows`. The error message is: 'KeyError: supabase_service_role_key not found in environment'. Please set the environment variable."

### For Technical Users:

1. **Check the terminal/logs** where the API is running
2. **Look for the error message** in the JSON response
3. **Use the request_id** to correlate with server logs
4. **Common 500 errors:**

| Error Message | Cause | Fix |
|---|---|---|
| `KeyError: supabase_service_role_key` | Missing environment variable | Set `SUPABASE_SERVICE_ROLE_KEY` in `.env` |
| `Connection refused to 127.0.0.1:54321` | Supabase not running | Run `supabase start` |
| `ModuleNotFoundError: No module named 'X'` | Missing dependency | Run `pip install -r requirements.txt` |
| `TypeError: unsupported operand type` | Code bug | Check the stack trace and fix the code |

---

## Testing the Fix

Run this to verify the API loads:
```bash
cd apps/api
python3 -c "from app.main import app; print('✓ API imports successfully')"
```

Expected output: `✓ API imports successfully`

Then start the API:
```bash
uvicorn app.main:app --reload --port 8000
```

Test an endpoint that should fail (missing auth):
```bash
curl http://localhost:8000/workflows
```

You should now see a proper error message explaining what went wrong, instead of generic "Internal server error".

---

## Files Modified

- [apps/api/app/main.py](../../apps/api/app/main.py)
  - Added `JSONResponse` import
  - Added `global_exception_handler` function

---

## Prevention: Best Practices

### 1. Always Use Try/Except in Route Handlers
```python
@app.post("/endpoint")
async def my_endpoint(request: MyRequest):
    try:
        result = await some_operation()
        return {"status": "success", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error in my_endpoint: %s", str(e), exc_info=e)
        raise HTTPException(status_code=500, detail="Internal error")
```

### 2. Log with Context
Always include request_id and relevant IDs:
```python
logger.error(
    "Failed to process workflow",
    exc_info=exc,
    extra={"workflow_id": workflow_id, "request_id": request_id}
)
```

### 3. Return Meaningful Error Messages
Don't just say "error occurred". Tell users why:
```python
# Bad
raise HTTPException(status_code=500, detail="Error")

# Good
raise HTTPException(status_code=500, detail="Failed to save workflow: database connection timeout")
```

---

## For Next Time: Tell Claude This

**Use this prompt when you need API error fixes:**

> "I'm getting a 500 error on the [ENDPOINT] endpoint. The error message is: [PASTE ERROR]. The endpoint is supposed to [DESCRIBE WHAT IT DOES]. Please fix it and add error handling if needed. Use compound engineering documentation."

**Example:**
> "I'm getting a 500 error on the /content_chat endpoint when I try to send a message. The error message is: 'ConnectionError: Failed to connect to OpenAI API'. The endpoint is supposed to generate content responses. Please fix it and add proper error handling."

---

## Related Documentation

- [docs/compound/architecture.md](./architecture.md) — API architecture overview
- [apps/api/README.md](../../apps/api/README.md) — API setup & deployment
- [HEARTBEAT.md](../../HEARTBEAT.md) — System health monitoring

---

**Last Updated:** 2026-02-25  
**Status:** RESOLVED ✅
