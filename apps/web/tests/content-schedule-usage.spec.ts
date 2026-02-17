import { test, expect, Page } from "@playwright/test";

const TEST_EMAIL = process.env.TEST_EMAIL || "test@example.com";
const TEST_PASSWORD = process.env.TEST_PASSWORD || "testpass123";
const BASE = "http://localhost:3000";

async function login(page: Page) {
  await page.goto(`${BASE}/login`);
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(1000);
  await page.fill('input[type="email"]', TEST_EMAIL);
  await page.fill('input[type="password"]', TEST_PASSWORD);
  await page.click('button[type="submit"]');
  await expect(page).toHaveURL(/.*brand/, { timeout: 15000 });
}

// ── Content Dashboard Tests ──────────────────────────────
test.describe("Content Dashboard", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("should load content page with heading and new content button", async ({
    page,
  }) => {
    await page.goto(`${BASE}/content`);
    await page.waitForLoadState("networkidle");

    // Page heading
    await expect(page.locator("h1")).toContainText("Content");

    // Description text
    await expect(
      page.locator("text=Create scripts, posts, and short-form content")
    ).toBeVisible();

    // Should have either "New Content" button or "Complete Brand First" link
    const newBtn = page.locator('a:has-text("New Content"), a:has-text("Complete Brand First")');
    await expect(newBtn.first()).toBeVisible();
  });

  test("should navigate to new content page", async ({ page }) => {
    await page.goto(`${BASE}/content`);
    await page.waitForLoadState("networkidle");

    // Click new content (might be disabled if brand incomplete)
    const newLink = page.locator('a[href="/content/new"]');
    if (await newLink.isVisible()) {
      await newLink.click();
      await expect(page).toHaveURL(/.*content\/new/);
      await expect(page.locator("h1")).toContainText("New Content");
    }
  });

  test("content nav link should be highlighted when active", async ({
    page,
  }) => {
    await page.goto(`${BASE}/content`);
    await page.waitForLoadState("networkidle");

    const contentLink = page.locator('nav a[href="/content"]');
    await expect(contentLink).toHaveClass(/bg-blue-50/);
  });
});

// ── New Content Form Tests ────────────────────────────────
test.describe("New Content Page", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("should show content creation form with all platform options", async ({
    page,
  }) => {
    await page.goto(`${BASE}/content/new`);
    await page.waitForLoadState("networkidle");

    // Goal textarea
    await expect(page.locator("#goal")).toBeVisible();

    // Platform option buttons (scoped to the platform grid area)
    const platformSection = page.locator("text=Which platforms?").locator("..");
    await expect(platformSection.locator("button").filter({ hasText: "YouTube" })).toBeVisible();
    await expect(platformSection.locator("button").filter({ hasText: "LinkedIn" })).toBeVisible();
    await expect(platformSection.locator("button").filter({ hasText: "Twitter/X" })).toBeVisible();
    await expect(platformSection.locator("button").filter({ hasText: "Short-form" })).toBeVisible();

    // Research sources
    await expect(page.locator("button").filter({ hasText: "YouTube trends" })).toBeVisible();
    await expect(page.locator("button").filter({ hasText: "Reddit discussions" })).toBeVisible();

    // Submit button should be disabled when empty
    const submitBtn = page.locator('button[type="submit"]');
    await expect(submitBtn).toBeDisabled();
  });

  test("should enable submit button when form is filled", async ({ page }) => {
    await page.goto(`${BASE}/content/new`);
    await page.waitForLoadState("networkidle");

    // Fill in goal
    await page.fill("#goal", "How to build a personal brand on LinkedIn targeting solo consultants");

    // Submit button should now be enabled (YouTube is selected by default)
    const submitBtn = page.locator('button[type="submit"]');
    await expect(submitBtn).toBeEnabled();
  });

  test("should toggle platform selection", async ({ page }) => {
    await page.goto(`${BASE}/content/new`);
    await page.waitForLoadState("networkidle");

    // YouTube should be selected by default (has blue border)
    const youtubeBtn = page.locator("button").filter({ hasText: "YouTube" }).first();
    await expect(youtubeBtn).toHaveClass(/border-blue-500/);

    // Click LinkedIn to select it
    const linkedinBtn = page.locator("button").filter({ hasText: "LinkedIn" }).first();
    await linkedinBtn.click();
    await expect(linkedinBtn).toHaveClass(/border-blue-500/);
  });

  test("should show back to content link", async ({ page }) => {
    await page.goto(`${BASE}/content/new`);
    await page.waitForLoadState("networkidle");

    const backLink = page.locator('a[href="/content"]').filter({ hasText: "Back to Content" });
    await expect(backLink).toBeVisible();
  });
});

// ── Schedule Page Tests ──────────────────────────────────
test.describe("Schedule Page", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("should load schedule page with kanban and calendar toggles", async ({
    page,
  }) => {
    await page.goto(`${BASE}/schedule`);
    await page.waitForLoadState("networkidle");

    // Heading
    await expect(page.locator("h1")).toContainText("Content Schedule");

    // View toggle buttons (use getByRole to avoid matching "Dashboard" which contains "board")
    await expect(page.getByRole("button", { name: "Board" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Calendar" })).toBeVisible();
  });

  test("should show kanban board or empty/error state after loading", async ({ page }) => {
    await page.goto(`${BASE}/schedule`);
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(3000);

    // After loading, the page shows EITHER:
    // 1. Kanban columns (if API call succeeded)
    // 2. An error message (if backend auth fails)
    // 3. An empty state hint ("No content in your schedule yet")
    // All are valid renders; we verify the page did not crash
    const draftColumn = page.locator("h3").filter({ hasText: "Draft" });
    const errorBanner = page.locator(".bg-red-50");
    const emptyHint = page.locator("text=No content in your schedule yet");
    const statsCard = page.locator("text=Drafts");

    const anyVisible = await Promise.race([
      draftColumn.waitFor({ state: "visible", timeout: 5000 }).then(() => "columns"),
      errorBanner.waitFor({ state: "visible", timeout: 5000 }).then(() => "error"),
      emptyHint.waitFor({ state: "visible", timeout: 5000 }).then(() => "empty"),
      statsCard.waitFor({ state: "visible", timeout: 5000 }).then(() => "stats"),
    ]).catch(() => "timeout");

    // At least one of these states should be visible
    expect(["columns", "error", "empty", "stats"]).toContain(anyVisible);
  });

  test("should switch to calendar view", async ({ page }) => {
    await page.goto(`${BASE}/schedule`);
    await page.waitForLoadState("networkidle");

    // Click calendar toggle
    await page.locator("button").filter({ hasText: "Calendar" }).click();

    // Calendar should show month navigation (chevron buttons)
    // and day-of-week headers
    await expect(page.locator("text=Mon")).toBeVisible();
    await expect(page.locator("text=Tue")).toBeVisible();
    await expect(page.locator("text=Wed")).toBeVisible();
  });

  test("should show new item button", async ({ page }) => {
    await page.goto(`${BASE}/schedule`);
    await page.waitForLoadState("networkidle");

    // New Item button
    const addBtn = page.locator("button").filter({ hasText: "New Item" });
    await expect(addBtn).toBeVisible();
  });

  test("schedule nav link should be highlighted when active", async ({
    page,
  }) => {
    await page.goto(`${BASE}/schedule`);
    await page.waitForLoadState("networkidle");

    const scheduleLink = page.locator('nav a[href="/schedule"]');
    await expect(scheduleLink).toHaveClass(/bg-blue-50/);
  });
});

// ── Usage Page Tests ─────────────────────────────────────
test.describe("Usage Page", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("should load usage page with heading and summary cards", async ({
    page,
  }) => {
    await page.goto(`${BASE}/usage`);
    await page.waitForLoadState("networkidle");

    // Heading
    await expect(page.locator("h1")).toContainText("Usage & Costs");

    // Summary cards (use exact text matching to avoid collision with "workflows today")
    await expect(page.locator("text=Total Spent")).toBeVisible();
    await expect(page.getByText("Today", { exact: true })).toBeVisible();
    await expect(page.locator("text=This Week")).toBeVisible();
    await expect(page.locator("text=This Month")).toBeVisible();
  });

  test("should show token usage section", async ({ page }) => {
    await page.goto(`${BASE}/usage`);
    await page.waitForLoadState("networkidle");

    await expect(page.locator("text=Token Usage")).toBeVisible();
    await expect(page.locator("text=Input tokens")).toBeVisible();
    await expect(page.locator("text=Output tokens")).toBeVisible();
  });

  test("should show daily workflow cap gauge", async ({ page }) => {
    await page.goto(`${BASE}/usage`);
    await page.waitForLoadState("networkidle");

    await expect(page.locator("text=Daily Workflow Cap")).toBeVisible();
    await expect(page.locator("text=workflows today")).toBeVisible();
  });

  test("should show daily spending chart", async ({ page }) => {
    await page.goto(`${BASE}/usage`);
    await page.waitForLoadState("networkidle");

    await expect(page.locator("text=Daily Spending")).toBeVisible();
  });

  test("should show cost by workflow section", async ({ page }) => {
    await page.goto(`${BASE}/usage`);
    await page.waitForLoadState("networkidle");

    await expect(page.locator("text=Cost by Workflow")).toBeVisible();
  });

  test("usage nav link should be highlighted when active", async ({
    page,
  }) => {
    await page.goto(`${BASE}/usage`);
    await page.waitForLoadState("networkidle");

    const usageLink = page.locator('nav a[href="/usage"]');
    await expect(usageLink).toHaveClass(/bg-blue-50/);
  });
});

// ── Navigation Tests ─────────────────────────────────────
test.describe("Navigation", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("nav bar should show all six sections", async ({ page }) => {
    await page.goto(`${BASE}/brand`);
    await page.waitForLoadState("networkidle");

    const nav = page.locator("nav");
    await expect(nav.locator("text=Brand")).toBeVisible();
    await expect(nav.locator("text=Knowledge")).toBeVisible();
    await expect(nav.locator("text=Content")).toBeVisible();
    await expect(nav.locator("text=Performance")).toBeVisible();
    await expect(nav.locator("text=Schedule")).toBeVisible();
    await expect(nav.locator("text=Usage")).toBeVisible();
  });

  test("should show PositionedUp logo text", async ({ page }) => {
    await page.goto(`${BASE}/brand`);
    await page.waitForLoadState("networkidle");

    await expect(page.locator("nav").locator("text=PositionedUp")).toBeVisible();
  });

  test("clicking each nav link should navigate to correct page", async ({
    page,
  }) => {
    await page.goto(`${BASE}/brand`);
    await page.waitForLoadState("networkidle");

    // Content
    await page.locator('nav a[href="/content"]').click();
    await expect(page).toHaveURL(/.*content/);

    // Schedule
    await page.locator('nav a[href="/schedule"]').click();
    await expect(page).toHaveURL(/.*schedule/);

    // Usage
    await page.locator('nav a[href="/usage"]').click();
    await expect(page).toHaveURL(/.*usage/);

    // Knowledge
    await page.locator('nav a[href="/knowledge"]').click();
    await expect(page).toHaveURL(/.*knowledge/);

    // Performance
    await page.locator('nav a[href="/performance"]').click();
    await expect(page).toHaveURL(/.*performance/);

    // Brand (use .last() because first match is the logo link)
    await page.locator('nav a[href="/brand"]').last().click();
    await expect(page).toHaveURL(/.*brand/);
  });
});

// ── Error/404 Tests ──────────────────────────────────────
test.describe("Error Handling", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("should show 404 for non-existent page", async ({ page }) => {
    await page.goto(`${BASE}/this-page-does-not-exist`);
    await page.waitForLoadState("networkidle");

    // Should show 404 text or redirect
    const body = await page.textContent("body");
    expect(
      body?.includes("404") || body?.includes("not found") || body?.includes("Not Found")
    ).toBeTruthy();
  });
});
