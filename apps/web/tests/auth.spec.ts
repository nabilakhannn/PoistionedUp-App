import { test, expect, Page } from "@playwright/test";

// Test credentials - create a test user in your Supabase dashboard
const TEST_EMAIL = process.env.TEST_EMAIL || "test@example.com";
const TEST_PASSWORD = process.env.TEST_PASSWORD || "testpass123";

/** Shared login helper — waits for hydration before interacting */
async function login(page: Page) {
  await page.goto("http://localhost:3000/login");
  await page.waitForLoadState("networkidle");
  // Small delay to ensure React hydration completes
  await page.waitForTimeout(1000);
  await page.fill('input[type="email"]', TEST_EMAIL);
  await page.fill('input[type="password"]', TEST_PASSWORD);
  await page.click('button[type="submit"]');
  await expect(page).toHaveURL(/.*brand/, { timeout: 15000 });
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
    await page.waitForTimeout(1000);

    await page.fill('input[type="email"]', "invalid@example.com");
    await page.fill('input[type="password"]', "wrongpassword");
    await page.click('button[type="submit"]');

    // Should show error message
    const errorDiv = page.locator(".bg-red-50");
    await expect(errorDiv).toBeVisible({ timeout: 10000 });
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
