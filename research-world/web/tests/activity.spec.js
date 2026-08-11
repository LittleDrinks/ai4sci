import { expect, test } from "@playwright/test";


async function openActivity(page, viewport) {
  await page.setViewportSize(viewport);
  await page.goto("/activity");
  await expect(page.getByText("Generation 0")).toBeVisible();
}


async function assertNoPageOverflow(page) {
  const widths = await page.evaluate(() => [document.documentElement.scrollWidth, innerWidth]);
  expect(widths[0]).toBeLessThanOrEqual(widths[1]);
}


async function assertViews(page) {
  await page.getByRole("button", { name: "Wire" }).click();
  await expect(page.locator(".wire-list details").first()).toBeVisible();
  await page.locator(".wire-list details").first().click();
  await expect(page.locator(".wire-list pre").first()).toBeVisible();
  await page.getByRole("button", { name: "Context" }).click();
  await expect(page.locator(".context-list details").first()).toBeVisible();
  await page.getByRole("button", { name: "Agents / Jobs" }).click();
  await expect(page.locator(".jobs-table tbody tr").first()).toBeVisible();
}


test("replays a completed run across all desktop views", async ({ page }) => {
  const errors = [];
  page.on("console", (message) => message.type() === "error" && errors.push(message.text()));
  await openActivity(page, { width: 1440, height: 1000 });
  await expect(page.getByText(/189 events/)).toBeVisible();
  await assertViews(page);
  await assertNoPageOverflow(page);
  expect(errors).toEqual([]);
  await page.screenshot({ path: "../evidence/activity-desktop.png" });
});


test("keeps all activity views usable on mobile", async ({ page }) => {
  await openActivity(page, { width: 390, height: 844 });
  await assertViews(page);
  await assertNoPageOverflow(page);
  await page.screenshot({ path: "../evidence/activity-mobile.png" });
});
