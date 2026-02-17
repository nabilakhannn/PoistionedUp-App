# Pattern: FastAPI Test Auth Override (autouse fixture)

**Date:** 2026-02-17
**Used in:** All backend test files that need authenticated endpoints

---

## Problem

Setting `app.dependency_overrides[get_current_user]` at module level in test files causes 401 errors because other test modules call `app.dependency_overrides.clear()` in their teardown, wiping the override for any test running after them.

## Solution

Use a pytest `autouse` fixture at the class level. This sets and clears the override for each test class, so no test module can interfere with another.

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth import get_current_user


class FakeUser:
    id = "test-user-001"
    email = "test@example.com"


class TestMyEndpoints:
    @pytest.fixture(autouse=True)
    def setup(self):
        app.dependency_overrides[get_current_user] = lambda: FakeUser()
        self.client = TestClient(app)
        yield
        app.dependency_overrides.clear()

    def test_something(self):
        resp = self.client.get("/my-endpoint")
        assert resp.status_code == 200
```

## Why this matters

- **Isolation**: Each test class gets its own clean override. No leaking between files.
- **Teardown safety**: `clear()` in `yield` runs even if a test fails.
- **No import order bugs**: Works regardless of which test file pytest discovers first.

## Related

Also: always use `upsert()` instead of `insert()` for seed data in integration tests that hit a real Supabase database. The auth trigger can auto-create rows (like profiles) on user signup, so `insert()` fails on re-runs with "duplicate key" errors.
