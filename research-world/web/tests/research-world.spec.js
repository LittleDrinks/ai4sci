import { expect, test } from "@playwright/test";


test("switches projects and drills from a cycle into attempt logs", async ({ page }) => {
  await page.goto("/roadmap");
  await expect(page.getByRole("heading", { name: "研究深度与前沿" })).toBeVisible();
  const projectId = await page.locator(".project-select option", { hasText: "Q049" }).getAttribute("value");
  await page.locator(".project-select select").selectOption(projectId);
  await expect(page.getByRole("heading", { name: "Baseline Conservative Dynamics Verification" })).toBeVisible();
  await page.getByRole("button", { name: /Baseline Conservative Dynamics Verification/ }).click();
  await expect(page.getByText("High-precision numerical integration", { exact: false })).toBeVisible();
  await page.locator(".result-inspector").getByRole("button", { name: "关闭" }).click();
  await page.locator(".road-work").filter({ hasText: "experiment" }).click();
  await expect(page.getByRole("heading", { name: "Workflow steps" })).toBeVisible();
  await expect(page.locator(".attempt-link").first()).toHaveAttribute("href", /\/api\/v1\/attempts\/.+\/log/);
});


test("leader and roadmap fit a phone viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  for (const path of ["/leader", "/roadmap"]) {
    await page.goto(path);
    await expect(page.locator("body")).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(1);
  }
});
