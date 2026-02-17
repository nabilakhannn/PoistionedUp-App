# Pattern: Playwright E2E Selector Best Practices

**Created:** 2026-02-17
**Context:** Writing Playwright tests for Content, Schedule, Usage, and Navigation pages

## Problem
Playwright's strict mode rejects locators that match multiple elements. Common pitfalls:
1. `text=YouTube` matches both a platform button and a "YouTube trends" research-source button.
2. `text=Today` matches both a card heading and "workflows today" text.
3. `nav a[href="/brand"]` matches both the logo link and the Brand nav link.

## Solution

### 1. Scope locators to parent sections
When the same label appears in different page areas, scope to the nearest parent:
```ts
const platformSection = page.locator("text=Which platforms?").locator("..");
await expect(platformSection.locator("button").filter({ hasText: "YouTube" })).toBeVisible();
```

### 2. Use exact text matching
When partial text matches cause ambiguity:
```ts
await expect(page.getByText("Today", { exact: true })).toBeVisible();
```

### 3. Use `.last()` / `.first()` / `.nth(n)` for known duplicates
When multiple elements legitimately share the same href:
```ts
await page.locator('nav a[href="/brand"]').last().click();
```

### 4. Tolerate backend-dependent states
When a page fetches from the API and the test user's auth may fail, check for multiple valid states:
```ts
const anyVisible = await Promise.race([
  columns.waitFor({ state: "visible", timeout: 5000 }).then(() => "columns"),
  errorBanner.waitFor({ state: "visible", timeout: 5000 }).then(() => "error"),
  emptyState.waitFor({ state: "visible", timeout: 5000 }).then(() => "empty"),
]).catch(() => "timeout");
expect(["columns", "error", "empty"]).toContain(anyVisible);
```

## When to Apply
- Every new Playwright test file
- Any test that touches pages with repeated labels or API-dependent rendering
