import { test, expect, Page } from "@playwright/test";

// Test credentials - create a test user in your Supabase dashboard
const TEST_EMAIL = process.env.TEST_EMAIL || "test@example.com";
const TEST_PASSWORD = process.env.TEST_PASSWORD || "testpass123";

/** Shared login helper — waits for full React hydration before interacting.
 *
 *  The login page is a "use client" component. After the initial HTML
 *  arrives, React must hydrate to attach onSubmit / onChange handlers.
 *  If we interact before hydration completes, the native form GET fires
 *  (URL becomes /login?) and React state stays empty.
 *
 *  Strategy:
 *    1. Wait for networkidle (all JS bundles loaded)
 *    2. Wait for the submit button to be *enabled* (React rendered)
 *    3. Use locator-based .fill() which auto-waits for actionability
 *    4. Type into fields, then verify React state updated by checking
 *       the input value attribute
 *    5. Submit via keyboard Enter (more reliable than clicking submit
 *       because it triggers from within a focused input, which React
 *       always handles)
 */
async function login(page: Page) {
  await page.goto("http://localhost:3000/login");
  await page.waitForLoadState("networkidle");

  // Wait for the submit button to be visible and interactive (hydration done)
  const submitBtn = page.locator('button[type="submit"]');
  await expect(submitBtn).toBeVisible({ timeout: 10000 });
  await expect(submitBtn).toBeEnabled({ timeout: 5000 });

  // Extra wait for React event handlers to attach after render
  await page.waitForTimeout(2000);

  // Fill fields using locators (auto-waits for actionability)
  const emailInput = page.locator('input[type="email"]');
  const passwordInput = page.locator('input[type="password"]');

  await emailInput.click();
  await emailInput.fill(TEST_EMAIL);
  await passwordInput.click();
  await passwordInput.fill(TEST_PASSWORD);

  // Small pause to let React state settle
  await page.waitForTimeout(500);

  // Submit via Enter key from the password field (avoids native form GET)
  await passwordInput.press("Enter");

  // Wait for redirect to /brand (login does window.location.href = "/brand")
  await expect(page).toHaveURL(/.*brand/, { timeout: 20000 });
}

test.describe("Authentication Flow", () => {
  test("should sign in, access protected page, and sign out", async ({
    page,
  }) => {
    await login(page);

    await page.goto("http://localhost:3000/brand/chat/foundation");
    await expect(page).toHaveURL(/.*foundation/);
    await expect(page.locator("main")).toBeVisible();

    await page.click('button:has-text("Sign out")');
    await expect(page).toHaveURL(/.*login/, { timeout: 10000 });
  });

  test("should reject invalid credentials", async ({ page }) => {
    await page.goto("http://localhost:3000/login");
    await page.waitForLoadState("networkidle");

    const submitBtn = page.locator('button[type="submit"]');
    await expect(submitBtn).toBeVisible({ timeout: 10000 });
    await expect(submitBtn).toBeEnabled({ timeout: 5000 });
    await page.waitForTimeout(2000);

    const emailInput = page.locator('input[type="email"]');
    const passwordInput = page.locator('input[type="password"]');

    await emailInput.click();
    await emailInput.fill("invalid@example.com");
    await passwordInput.click();
    await passwordInput.fill("wrongpassword");
    await page.waitForTimeout(500);

    await passwordInput.press("Enter");

    // Should show error message
    const errorDiv = page.locator(".bg-red-50");
    await expect(errorDiv).toBeVisible({ timeout: 15000 });
  });

  test("should redirect unauthenticated users to login", async ({ page }) => {
    await page.goto("http://localhost:3000/brand");
    await expect(page).toHaveURL(/.*login/, { timeout: 10000 });
  });

  test("should prevent authenticated users from accessing login page", async ({
    page,
  }) => {
    await login(page);
    await page.goto("http://localhost:3000/login");
    await expect(page).toHaveURL(/.*brand/, { timeout: 10000 });
  });
});
