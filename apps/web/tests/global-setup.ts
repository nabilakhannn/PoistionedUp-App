/**
 * Playwright Global Setup — Login Once, Reuse Session
 *
 * Runs once before all tests. If TEST_EMAIL + TEST_PASSWORD are set,
 * logs in and saves the browser storage state (cookies + localStorage)
 * to tests/.auth-state.json. Tests then load this state instead of
 * repeating the login for every describe block.
 */

import { chromium, FullConfig } from "@playwright/test";
import path from "path";
import fs from "fs";

export const AUTH_STATE_PATH = path.join(__dirname, ".auth-state.json");

export default async function globalSetup(config: FullConfig) {
  const email = process.env.TEST_EMAIL;
  const password = process.env.TEST_PASSWORD;

  // No credentials → skip auth setup. Unauthenticated tests still run.
  if (!email || !password) {
    console.log("[global-setup] No TEST_EMAIL/TEST_PASSWORD — skipping auth setup");
    return;
  }

  const baseURL = config.projects[0].use.baseURL ?? "http://localhost:3000";

  console.log(`[global-setup] Logging in as ${email}…`);
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    await page.goto(`${baseURL}/login`, { waitUntil: "domcontentloaded" });

    // Wait for the sign-in form to be ready
    await page.waitForSelector('input[type="email"]', { timeout: 15000 });
    await page.fill('input[type="email"]', email);
    await page.fill('input[type="password"]', password);

    // Submit — press Enter on the password field (works regardless of button type)
    await page.locator('input[type="password"]').press("Enter");

    // Wait for redirect to /brands or /onboarding
    await page.waitForURL(/(brands|onboarding)/, { timeout: 25000 });
    console.log(`[global-setup] Authenticated — landed at ${page.url()}`);

    // Persist cookies + localStorage so tests start pre-authenticated
    await context.storageState({ path: AUTH_STATE_PATH });
    console.log(`[global-setup] Auth state saved to ${AUTH_STATE_PATH}`);
  } catch (err) {
    console.error("[global-setup] Login failed:", err);
    // Don't throw — unauthenticated tests can still run; auth tests will skip
  } finally {
    await browser.close();
  }
}
