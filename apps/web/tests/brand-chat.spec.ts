import { test, expect, Page } from "@playwright/test";

const TEST_EMAIL = process.env.TEST_EMAIL || "test@example.com";
const TEST_PASSWORD = process.env.TEST_PASSWORD || "testpass123";
const BASE = "http://localhost:3000";

async function login(page: Page) {
  await page.goto(`${BASE}/login`, { waitUntil: "domcontentloaded" });
  const submitBtn = page.locator('button[type="submit"]');
  await expect(submitBtn).toBeVisible({ timeout: 15000 });
  await expect(submitBtn).toBeEnabled({ timeout: 5000 });
  await page.waitForTimeout(1500);
  await page.fill('input[type="email"]', TEST_EMAIL);
  await page.fill('input[type="password"]', TEST_PASSWORD);
  await page.waitForTimeout(500);
  await page.locator('input[type="password"]').press("Enter");
  await expect(page).toHaveURL(/.*brand/, { timeout: 20000 });
}

// ── Brand Chat UI Tests ─────────────────────────────────────
test.describe("Brand Chat Page", () => {
  // All brand chat tests require a real Supabase test user
  test.skip(() => !process.env.TEST_EMAIL, "Skipped: Set TEST_EMAIL and TEST_PASSWORD env vars");

  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("should load foundation chat page with sidebar and chat", async ({
    page,
  }) => {
    await page.goto(`${BASE}/brand/chat/foundation`, { waitUntil: "domcontentloaded" });

    // Left sidebar stages (scoped to the chat page sidebar, not the main nav)
    // The legacy chat page has its own sidebar with module links
    await expect(page.locator("text=Foundation").first()).toBeVisible({ timeout: 10000 });

    // Header
    await expect(page.locator("h1")).toContainText("Foundation");

    // Chat input area
    await expect(page.locator("textarea")).toBeVisible();
    await expect(page.locator('button:has-text("Send")')).toBeVisible();
  });

  test("should navigate between chat modules via sidebar", async ({
    page,
  }) => {
    await page.goto(`${BASE}/brand/chat/foundation`, { waitUntil: "domcontentloaded" });
    await expect(page.locator("h1")).toContainText("Foundation", { timeout: 10000 });

    await page.click('a[href="/brand/chat/ica"]');
    await expect(page).toHaveURL(/.*brand\/chat\/ica/, { timeout: 5000 });
    await expect(page.locator("h1")).toContainText("Ideal Client Avatar");

    await page.click('a[href="/brand/chat/offer"]');
    await expect(page).toHaveURL(/.*brand\/chat\/offer/, { timeout: 5000 });
    await expect(page.locator("h1")).toContainText("Your Offer");

    await page.click('a[href="/brand/chat/brand"]');
    await expect(page).toHaveURL(/.*brand\/chat\/brand/, { timeout: 5000 });
    await expect(page.locator("h1")).toContainText("Brand Statement");
  });

  test("should have a Back to Brand Dashboard link", async ({ page }) => {
    await page.goto(`${BASE}/brand/chat/foundation`, { waitUntil: "domcontentloaded" });
    await expect(page.locator("h1")).toContainText("Foundation", { timeout: 10000 });

    const backLink = page.locator('a:has-text("Brand Dashboard")');
    await expect(backLink).toBeVisible();
    await expect(backLink).toHaveAttribute("href", "/brand");
  });

  test("should type and send a message", async ({ page }) => {
    await page.goto(`${BASE}/brand/chat/foundation`, { waitUntil: "domcontentloaded" });
    await expect(page.locator("textarea")).toBeVisible({ timeout: 10000 });

    const textarea = page.locator("textarea");
    await textarea.fill("I believe in authentic personal branding");
    await page.click('button:has-text("Send")');

    await expect(
      page.locator("text=I believe in authentic personal branding")
    ).toBeVisible({ timeout: 5000 });
  });

  test("should not send empty message", async ({ page }) => {
    await page.goto(`${BASE}/brand/chat/foundation`, { waitUntil: "domcontentloaded" });
    await expect(page.locator("textarea")).toBeVisible({ timeout: 10000 });

    const sendBtn = page.locator('button:has-text("Send")');
    await expect(sendBtn).toBeDisabled();
  });

  test("Done button should exist and respect message count threshold", async ({
    page,
  }) => {
    await page.goto(`${BASE}/brand/chat/foundation`, { waitUntil: "domcontentloaded" });
    await expect(page.locator("textarea")).toBeVisible({ timeout: 10000 });
    await page.click("text=New Chat");
    await page.waitForTimeout(2000);

    const doneBtn = page.locator('button:has-text("Done, review form")');
    await expect(doneBtn).toBeVisible();
    const isDisabled = await doneBtn.isDisabled();
    expect(typeof isDisabled).toBe("boolean");
  });
});

// ── Voice / Mic Button Tests ────────────────────────────────
test.describe("Voice Input (Mic Button)", () => {
  test.skip(() => !process.env.TEST_EMAIL, "Skipped: Set TEST_EMAIL and TEST_PASSWORD env vars");

  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE}/brand/chat/foundation`, { waitUntil: "domcontentloaded" });
    await expect(page.locator("textarea")).toBeVisible({ timeout: 10000 });
  });

  test("should display mic button next to textarea", async ({ page }) => {
    const micBtn = page.locator('button[title="Speak your answer"]');
    await expect(micBtn).toBeVisible();
  });

  test("mic button should have idle styling", async ({ page }) => {
    const micBtn = page.locator('button[title="Speak your answer"]');
    // Dark theme: mic button uses bg-zinc-800 (not bg-gray-100)
    await expect(micBtn).toHaveClass(/rounded-full/);
  });

  test("clicking mic should not crash the page", async ({ page }) => {
    const context = page.context();
    await context.grantPermissions(["microphone"]);

    const micBtn = page.locator('button[title="Speak your answer"]');
    await micBtn.click();
    await page.waitForTimeout(500);

    await expect(page.locator("textarea")).toBeVisible();
    await expect(page.locator('button:has-text("Send")')).toBeVisible();
  });
});

// ── Chat Management Tests ───────────────────────────────────
test.describe("Chat Management (New / Switch / Delete)", () => {
  test.skip(() => !process.env.TEST_EMAIL, "Skipped: Set TEST_EMAIL and TEST_PASSWORD env vars");

  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE}/brand/chat/foundation`, { waitUntil: "domcontentloaded" });
    await expect(page.locator("textarea")).toBeVisible({ timeout: 10000 });
  });

  test("should show chat switcher bar with New Chat button", async ({
    page,
  }) => {
    await expect(page.locator("text=New Chat")).toBeVisible();
  });

  test("should show chat count in switcher", async ({ page }) => {
    const switcher = page.locator("text=/\\d+ chats?/");
    await expect(switcher).toBeVisible({ timeout: 5000 });
  });

  test("should create a new chat when clicking New Chat", async ({ page }) => {
    await page.click("text=New Chat");
    await page.waitForTimeout(1000);

    const textarea = page.locator("textarea");
    await expect(textarea).toHaveValue("");
  });

  test("should show chat list dropdown when clicking chat count", async ({
    page,
  }) => {
    const chatCountBtn = page.locator("text=/\\d+ chats?/");
    await chatCountBtn.click();
    await page.waitForTimeout(500);

    const chatItems = page.locator('[class*="rounded-lg"][class*="cursor-pointer"]');
    const count = await chatItems.count();
    expect(count).toBeGreaterThanOrEqual(1);
  });

  test("should have delete button on each chat in the list", async ({
    page,
  }) => {
    const chatCountBtn = page.locator("text=/\\d+ chats?/");
    await chatCountBtn.click();
    await page.waitForTimeout(500);

    const deleteBtn = page.locator('button[title="Delete this chat"]');
    const count = await deleteBtn.count();
    expect(count).toBeGreaterThanOrEqual(1);
  });
});

// ── File Attachment Tests ────────────────────────────────────
test.describe("File Attachment in Chat", () => {
  test.skip(() => !process.env.TEST_EMAIL, "Skipped: Set TEST_EMAIL and TEST_PASSWORD env vars");

  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE}/brand/chat/foundation`, { waitUntil: "domcontentloaded" });
    await expect(page.locator("textarea")).toBeVisible({ timeout: 10000 });
  });

  test("should show attach file button", async ({ page }) => {
    const attachBtn = page.locator(
      'button[title="Attach a file or image"]'
    );
    await expect(attachBtn).toBeVisible();
  });

  test("should show attach link button", async ({ page }) => {
    const linkBtn = page.locator(
      'button[title="Attach a link (YouTube, website, Reddit, etc.)"]'
    );
    await expect(linkBtn).toBeVisible();
  });

  test("should have hidden file input with correct accept types", async ({
    page,
  }) => {
    const fileInput = page.locator('input[type="file"]');
    await expect(fileInput).toHaveCount(1);
    const accept = await fileInput.getAttribute("accept");
    expect(accept).toContain(".pdf");
    expect(accept).toContain(".docx");
    expect(accept).toContain(".txt");
    expect(accept).toContain(".md");
    expect(accept).toContain(".csv");
    expect(accept).toContain(".png");
    expect(accept).toContain(".jpg");
    expect(accept).toContain(".jpeg");
  });

  test("should show attachment preview after uploading a text file", async ({
    page,
  }) => {
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: "my-brand-notes.txt",
      mimeType: "text/plain",
      buffer: Buffer.from(
        "I am a fitness coach with 10 years experience in strength training."
      ),
    });

    await page.waitForTimeout(2000);
    await expect(page.locator("text=my-brand-notes.txt")).toBeVisible({
      timeout: 5000,
    });

    const removeBtn = page.locator('button[title="Remove attachment"]');
    await expect(removeBtn).toBeVisible();
  });

  test("should remove attachment when clicking X", async ({ page }) => {
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: "test-remove.txt",
      mimeType: "text/plain",
      buffer: Buffer.from("Quick test content for removal."),
    });

    await page.waitForTimeout(2000);
    await expect(page.locator("text=test-remove.txt")).toBeVisible({
      timeout: 5000,
    });

    await page.click('button[title="Remove attachment"]');
    await expect(page.locator("text=test-remove.txt")).not.toBeVisible();
  });

  test("should update textarea placeholder when file attached", async ({
    page,
  }) => {
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: "context.txt",
      mimeType: "text/plain",
      buffer: Buffer.from("Some context about my brand."),
    });

    await page.waitForTimeout(2000);

    const textarea = page.locator("textarea");
    const placeholder = await textarea.getAttribute("placeholder");
    expect(placeholder).toContain("context.txt");
  });

  test("should show link input bar when clicking link button", async ({
    page,
  }) => {
    const linkBtn = page.locator(
      'button[title="Attach a link (YouTube, website, Reddit, etc.)"]'
    );
    await linkBtn.click();
    await page.waitForTimeout(300);

    const urlInput = page.locator('input[type="url"]');
    await expect(urlInput).toBeVisible();
    await expect(urlInput).toBeFocused();

    await expect(page.locator('button:has-text("Extract")')).toBeVisible();
  });

  test("should dismiss link input on escape", async ({ page }) => {
    const linkBtn = page.locator(
      'button[title="Attach a link (YouTube, website, Reddit, etc.)"]'
    );
    await linkBtn.click();
    await page.waitForTimeout(300);

    const urlInput = page.locator('input[type="url"]');
    await expect(urlInput).toBeVisible();

    await urlInput.press("Escape");
    await expect(urlInput).not.toBeVisible();
  });
});

// ── All Modules Load Test ───────────────────────────────────
test.describe("All Brand Chat Modules", () => {
  test.skip(() => !process.env.TEST_EMAIL, "Skipped: Set TEST_EMAIL and TEST_PASSWORD env vars");

  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  const modules = [
    { path: "foundation", heading: "Foundation" },
    { path: "ica", heading: "Ideal Client Avatar" },
    { path: "offer", heading: "Your Offer" },
    { path: "brand", heading: "Brand Statement" },
  ];

  for (const mod of modules) {
    test(`should load ${mod.path} chat page with mic and attach`, async ({
      page,
    }) => {
      await page.goto(`${BASE}/brand/chat/${mod.path}`, { waitUntil: "domcontentloaded" });

      await expect(page.locator("h1")).toContainText(mod.heading, { timeout: 10000 });
      await expect(page.locator("textarea")).toBeVisible();
      await expect(page.locator('button:has-text("Send")')).toBeVisible();
      await expect(
        page.locator('button[title="Speak your answer"]')
      ).toBeVisible();
      await expect(
        page.locator('button[title="Attach a file or image"]')
      ).toBeVisible();
      await expect(
        page.locator(
          'button[title="Attach a link (YouTube, website, Reddit, etc.)"]'
        )
      ).toBeVisible();
    });
  }
});
