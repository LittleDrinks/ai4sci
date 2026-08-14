import { expect, test } from "@playwright/test";


test("renders persisted graph nodes without presentation metadata", async ({ page }) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.route(/\/api\/v1\/bootstrap/, (route) => route.fulfill({ json: mapFixture() }));
  await page.goto("/map");
  await expect(page.getByText("研究地图").first()).toBeVisible();
  await expect(page.locator(".research-node")).toBeVisible();
  expect(errors).toEqual([]);
});


function mapFixture() {
  const node = { id: "node:question", project_id: "project:test", kind: "question", payload: { text: "Why?" }, status: "admitted", created_at: "2026-08-14T00:00:00Z" };
  return { projects: [{ id: "project:test", title: "Test" }], active_project_id: "project:test",
    nodes: [node], review_nodes: [node], edges: [], events: [], jobs: [], agents: [], runtimes: [], artifacts: [], runs: [] };
}
