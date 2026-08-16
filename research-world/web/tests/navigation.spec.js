import { expect, test } from "@playwright/test";


function fixture() {
  const question = { id: "node:q", project_id: "project:test", parent_id: null, lineage_id: "lineage:q", kind: "question", payload: { text: "如何验证新方向？" },
    life_state: "admitted", direction_status: null, working: 0, rejection_reason: null, rebuttal: null, created_at: "2026-08-16T00:00:00Z", updated_at: "2026-08-16T00:00:00Z" };
  return { projects: [{ id: "project:test", title: "测试项目", question: "如何验证新方向？", auto: 0, node_count: 1, workflow_count: 0, created_at: "2026-08-16T00:00:00Z" }],
    active_project_id: "project:test", nodes: [question], edges: [], workflows: [], slots: [{ index: 1, workflow: null }, { index: 2, workflow: null }] };
}


async function mockNavigation(page) {
  await page.route(/\/api\/v1\/bootstrap/, (route) => route.fulfill({ json: fixture() }));
  await page.route(/\/api\/v1\/projects\/project%3Atest\/messages/, (route) => route.fulfill({ json: [] }));
}


test("keeps project selection outside the application shell", async ({ page }) => {
  await mockNavigation(page);
  await page.goto("/projects");
  await expect(page.getByRole("heading", { name: "选择研究项目" })).toBeVisible();
  await expect(page.locator(".sidebar")).toHaveCount(0);
  await page.screenshot({ path: "test-results/projects-desktop.png" });
  await page.locator(".project-list > button").click();
  await expect(page).toHaveURL(/\/map$/);
  await expect(page.locator(".sidebar nav a")).toHaveCount(3);
  await page.getByRole("button", { name: "退出项目" }).click();
  await expect(page).toHaveURL(/\/projects$/);
});


test("redirects removed routes to project selection", async ({ page }) => {
  await mockNavigation(page);
  await page.goto("/review");
  await expect(page).toHaveURL(/\/projects$/);
  await expect(page.getByRole("heading", { name: "选择研究项目" })).toBeVisible();
});


test("persists the color theme", async ({ page }) => {
  await mockNavigation(page);
  await page.goto("/projects");
  await page.getByRole("button", { name: "切换深色模式" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.screenshot({ path: "test-results/projects-dark.png" });
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
});
