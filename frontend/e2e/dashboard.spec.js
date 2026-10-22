import { test, expect } from "@playwright/test";
import { readFile } from "node:fs/promises";

async function loadSample(page) {
  await page.goto("/");
  await page.getByRole("button", { name: "Load sample data" }).click();
  await expect(page.getByText("Showing 4 of 4 alerts")).toBeVisible();
}

test("sample, charts, filters, details, export, and clear results", async ({
  page,
}) => {
  await loadSample(page);
  await expect(page.locator(".metric strong")).toHaveText([
    "19",
    "4",
    "0",
    "0",
  ]);
  await expect(page.getByRole("img")).toHaveAccessibleName(/5 failures/);
  await expect(page.locator("tbody tr")).toHaveCount(4);
  await page.getByRole("combobox", { name: "Severity", exact: true }).selectOption("high");
  await expect(page.locator("tbody tr")).toHaveCount(1);
  await page
    .getByRole("button", { name: /Review Success after failures/ })
    .click();
  await expect(
    page.getByRole("region", { name: "Selected alert details" }),
  ).toContainText("target_b");
  await page.getByRole("button", { name: "Close details" }).click();
  await page
    .getByRole("combobox", { name: "Detection rule", exact: true })
    .selectOption("repeated_failed_logins");
  await expect(page.getByText("No alerts match these filters")).toBeVisible();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export all alerts" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("alerts.csv");
  const csv = await readFile(await download.path(), "utf8");
  expect(csv).toContain("success_after_failures");
  expect(csv.trim().split("\r\n")).toHaveLength(5);
  await page.getByRole("button", { name: "Clear results" }).click();
  await expect(page.getByText("Your investigation starts here")).toBeVisible();
});

test("rule edits are applied by Python and previous results keep their config", async ({
  page,
}) => {
  await loadSample(page);
  await page
    .getByRole("button", { name: "Detection rules", exact: true })
    .click();
  const thresholds = page.getByLabel(/^Threshold/);
  await thresholds.nth(0).fill("6");
  await thresholds.nth(1).fill("4");
  await thresholds.nth(2).fill("6");
  await page.getByRole("button", { name: "Apply rules" }).click();
  await expect(page.getByRole("status")).toContainText("Rules applied");
  await page.getByRole("button", { name: "Overview", exact: true }).click();
  await expect(page.getByText("Showing 4 of 4 alerts")).toBeVisible();
  await page.getByRole("button", { name: "Load sample data" }).click();
  await expect(page.getByText("No rules triggered")).toBeVisible();
  await expect(page.locator(".metric strong")).toHaveText([
    "19",
    "0",
    "0",
    "0",
  ]);
});

test("upload runs through the API and displays duplicate and invalid-row counts", async ({
  page,
}) => {
  await page.goto("/");
  const csv =
    "timestamp,username,source_ip,event_type,status\n2026-01-01T00:00:00Z,a,192.0.2.1,login,success\n2026-01-01T00:00:00Z,a,192.0.2.1,login,success\nbad,a,192.0.2.1,login,failure";
  await page
    .getByLabel("Authentication CSV")
    .setInputFiles({
      name: "quality.csv",
      mimeType: "text/csv",
      buffer: Buffer.from(csv),
    });
  await page.getByRole("button", { name: "Analyze CSV" }).click();
  await expect(page.locator(".metric strong")).toHaveText(["1", "0", "1", "1"]);
  await page.getByText("1 data-quality warnings").click();
  await expect(page.getByText(/Line 4: invalid/)).toBeVisible();
});

test("loading, failed requests, invalid files, and mobile navigation", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page
    .getByLabel("Authentication CSV")
    .setInputFiles({
      name: "bad.txt",
      mimeType: "text/plain",
      buffer: Buffer.from("bad"),
    });
  await expect(page.getByRole("alert")).toContainText("ending in .csv");
  let release;
  const gate = new Promise((resolve) => {
    release = resolve;
  });
  await page.route("**/api/sample?*", async (route) => {
    await gate;
    await route.fulfill({
      status: 400,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Invalid test CSV" }),
    });
  });
  await page.getByRole("button", { name: "Load sample data" }).click();
  await expect(page.getByText("Running Python detection rules…")).toBeVisible();
  release();
  await expect(page.getByRole("alert")).toContainText("Invalid test CSV");
  await expect(page.getByText("Your investigation starts here")).toBeVisible();
  await page.getByRole("button", { name: "About this tool" }).click();
  await expect(
    page.getByRole("heading", { name: "Privacy & ethical use" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});
