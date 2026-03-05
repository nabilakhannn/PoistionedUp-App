/**
 * E2E Unauthenticated Tests — Slices 88–101
 *
 * These tests require NO login and run in every environment:
 *   - Protected route redirects to /login
 *   - Public routes (login, signup, intake, share) load without auth
 *   - Vercel API health checks (live endpoints return expected status codes)
 *
 * Authenticated tests → see new-features-auth.spec.ts
 * Run auth tests:  TEST_EMAIL=x TEST_PASSWORD=y npx playwright test tests/new-features-auth.spec.ts
 */

import { test, expect } from "@playwright/test";

const BASE = "http://localhost:3000";

// ── Protected Route Redirects ────────────────────────────────────────────────

test.describe("Protected route redirects (no auth required)", () => {
  const protectedRoutes = [
    "/mission-control",
    "/sales",
    "/marketing",
    "/intelligence",
    "/deliverables",
    "/mission-control/clients",
    "/mission-control/playbooks",
    "/mission-control/ledger",
    "/mission-control/settings",
    "/mission-control/competitors",
    "/mission-control/qa",
    "/mission-control/analytics",
    "/mission-control/gateway",
    "/mission-control/chat",
    "/composer",
    "/brands",
    "/research",
    "/usage",
    "/performance",
  ];

  for (const route of protectedRoutes) {
    test(`${route} redirects to /login`, async ({ page }) => {
      await page.goto(`${BASE}${route}`, { waitUntil: "domcontentloaded" });
      await expect(page).toHaveURL(/.*login/, { timeout: 15000 });
    });
  }
});

// ── Public Routes ────────────────────────────────────────────────────────────

test.describe("Public routes load without authentication", () => {
  test("login page loads with email + password fields", async ({ page }) => {
    await page.goto(`${BASE}/login`, { waitUntil: "domcontentloaded" });
    await expect(page.locator('input[type="email"]')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test("signup page loads with email + password fields", async ({ page }) => {
    await page.goto(`${BASE}/signup`, { waitUntil: "domcontentloaded" });
    await expect(page.locator('input[type="email"]')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test("intake page with invalid token shows error or form", async ({ page }) => {
    await page.goto(`${BASE}/intake/invalid-token-000`, { waitUntil: "domcontentloaded" });
    await expect(page).not.toHaveURL(/.*login/, { timeout: 5000 });
    await page.waitForTimeout(3000);
    const bodyText = await page.locator("body").textContent();
    expect(bodyText && bodyText.trim().length).toBeGreaterThan(0);
  });

  test("share page with invalid token shows error or content", async ({ page }) => {
    await page.goto(`${BASE}/share/invalid-token-000`, { waitUntil: "domcontentloaded" });
    await expect(page).not.toHaveURL(/.*login/, { timeout: 5000 });
    const hasContent = await page.locator("main").isVisible().catch(() => false);
    expect(hasContent).toBe(true);
  });
});

// ── API Health Check (live Vercel) ───────────────────────────────────────────

test.describe("API Health Check", () => {
  test("Vercel API /health returns ok", async ({ request }) => {
    const response = await request.get("https://api-iota-puce.vercel.app/health");
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body.status).toBe("ok");
    expect(body.db).toBe("connected");
  });

  test("brand-chat route exists (returns 401 without token)", async ({ request }) => {
    const response = await request.post(
      "https://api-iota-puce.vercel.app/brand-chat/00000000-0000-0000-0000-000000000000",
      { data: { message: "test" } }
    );
    expect([401, 403, 422]).toContain(response.status());
  });

  test("leads route exists (returns 401 without token)", async ({ request }) => {
    const response = await request.get("https://api-iota-puce.vercel.app/leads");
    expect([401, 403]).toContain(response.status());
  });

  test("pipeline run-now route exists (returns 401 without token)", async ({ request }) => {
    const response = await request.post(
      "https://api-iota-puce.vercel.app/pipeline/run-now"
    );
    expect([401, 403, 422]).toContain(response.status());
  });

  test("icp-research route exists (returns 401 without token)", async ({ request }) => {
    const response = await request.post(
      "https://api-iota-puce.vercel.app/leads/icp-research",
      { data: { brand_id: "00000000-0000-0000-0000-000000000000" } }
    );
    expect([401, 403, 422]).toContain(response.status());
  });

  test("icp-methodology route exists (returns 401 without token)", async ({ request }) => {
    const response = await request.get(
      "https://api-iota-puce.vercel.app/leads/icp-methodology"
    );
    expect([401, 403]).toContain(response.status());
  });
});
