import { expect, test } from "@playwright/test";


function workflow(state = {}) {
  return { id: "workflow:trace01", project_id: "project:test", node_id: "node:d", lineage_id: "lineage:alpha", kind: "plan-execute-review-reflect",
    stage: "review", status: "running", payload: {}, auto: 1, created_at: "2026-08-16T10:00:00Z", updated_at: "2026-08-16T10:01:12Z",
    steps: [{ id: "step:1", ordinal: 1, stage: "execute", status: "completed", requires_confirmation: 0, payload: {}, output: {}, started_at: "2026-08-16T10:00:10Z", completed_at: "2026-08-16T10:00:42Z" }],
    events: [{ id: 1, actor: "planner", type: "assistant", payload: { text: "已生成最小实验计划" }, time: "2026-08-16T10:00:08Z" },
      { id: 2, actor: "runner", type: "tool_result", payload: { command: "pytest -q", exit_code: 0 }, time: "2026-08-16T10:00:42Z" },
      { id: 3, actor: "reviewer-a", type: "assistant", payload: { summary: "机械审计通过，证据完整" }, time: "2026-08-16T10:01:12Z" }], ...state };
}


function fixture(item = workflow()) {
  return { projects: [{ id: "project:test", title: "测试项目", question: "怎样验证这个方向？", auto: 1 }], active_project_id: "project:test", nodes: [], edges: [], workflows: [item],
    slots: [{ index: 1, workflow: item }, { index: 2, workflow: null }] };
}


async function mockActivity(page, body = fixture()) {
  await page.route(/\/api\/v1\/bootstrap/, (route) => route.fulfill({ json: body }));
}


test("renders the DSH metrics, role rows and bottom statistics", async ({ page }) => {
  await mockActivity(page);
  await page.goto("/activity");
  await expect(page.getByText("Duration")).toBeVisible();
  await expect(page.getByText("Turns")).toBeVisible();
  await expect(page.getByText("Calls")).toBeVisible();
  await expect(page.getByText("TOOL")).toBeVisible();
  await expect(page.getByText("ASSISTANT").first()).toBeVisible();
  await expect(page.locator(".trace-bottom")).toContainText("完成步骤 1/1");
  await page.screenshot({ path: "test-results/activity-dsh.png" });
});


test("reduces the queue to occupied and idle slot indicators", async ({ page }) => {
  await mockActivity(page);
  await page.goto("/activity");
  await expect(page.getByLabel("执行槽位").getByText("槽位 1")).toBeVisible();
  await expect(page.getByLabel("执行槽位").getByText("空闲")).toBeVisible();
  await expect(page.getByRole("navigation", { name: "工作流" })).toBeVisible();
});


test("continues a manual workflow from the activity trace", async ({ page }) => {
  const item = workflow({ status: "waiting_human", stage: "execute", auto: 0 });
  let confirmed = false;
  await mockActivity(page, fixture(item));
  await page.route(/\/api\/v1\/workflows\/workflow%3Atrace01\/confirm/, (route) => { confirmed = true; return route.fulfill({ status: 202, json: item }); });
  await page.goto("/activity");
  await page.getByRole("button", { name: "继续执行" }).click();
  await expect.poll(() => confirmed).toBe(true);
});


test("keeps the activity trace readable on mobile", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockActivity(page);
  await page.goto("/activity");
  await expect(page.getByText("TOOL")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await page.screenshot({ path: "test-results/activity-mobile.png", fullPage: true });
  await page.locator(".trace-bottom").scrollIntoViewIfNeeded();
  await expect(page.locator(".trace-bottom")).toBeVisible();
});
