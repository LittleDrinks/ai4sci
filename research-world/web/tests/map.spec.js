import { expect, test } from "@playwright/test";


function node(id, kind, state = {}) {
  return { id, project_id: "project:test", parent_id: null, lineage_id: `lineage:${id}`,
    kind, payload: { text: `${kind} node` }, life_state: "admitted", direction_status: kind === "direction" ? "proposed" : null,
    working: 0, rejection_reason: null, rebuttal: null, created_at: "2026-08-16T00:00:00Z", updated_at: "2026-08-16T00:00:00Z", ...state };
}


function fixture() {
  const nodes = [node("node:q", "question"), node("node:s", "source"), node("node:d", "direction"), node("node:e", "experiment")];
  return { projects: [{ id: "project:test", title: "测试项目", question: "Why?", auto: 0 }], active_project_id: "project:test", nodes,
    edges: [{ source: "node:s", target: "node:d", polarity: "supports" }, { source: "node:e", target: "node:d", polarity: "refutes" }], workflows: [], slots: [{ index: 1, workflow: null }, { index: 2, workflow: null }] };
}


async function mockMap(page, body = fixture()) {
  await page.route(/\/api\/v1\/bootstrap/, (route) => route.fulfill({ json: body }));
  await page.route(/\/api\/v1\/projects\/project%3Atest\/messages/, (route) => route.request().method() === "GET" ? route.fulfill({ json: [] }) : route.fulfill({ status: 201, json: { id: 1, role: "assistant", content: "已带入上下文" } }));
}


function nodeX(page, id) {
  return page.locator(`.react-flow__node[data-id="${id}"]`).evaluate((element) => new DOMMatrixReadOnly(getComputedStyle(element).transform).m41);
}


test("lays out the four fixed node kinds as graph lanes", async ({ page }) => {
  await mockMap(page);
  await page.goto("/map");
  await expect(page.locator(".research-node")).toHaveCount(4);
  expect(await nodeX(page, "node:s")).toBeGreaterThan(await nodeX(page, "node:q"));
  expect(await nodeX(page, "node:d")).toBeGreaterThan(await nodeX(page, "node:s"));
  expect(await nodeX(page, "node:e")).toBeGreaterThan(await nodeX(page, "node:d"));
});


test("shows pending, working and ghost life states", async ({ page }) => {
  const body = fixture();
  body.nodes[1] = node("node:s", "source", { life_state: "pending" });
  body.nodes[2] = node("node:d", "direction", { working: 1 });
  body.nodes[3] = node("node:e", "experiment", { life_state: "ghost", rejection_reason: "机械审计失败" });
  await mockMap(page, body);
  await page.goto("/map");
  await expect(page.locator(".life-pending")).toBeVisible();
  await expect(page.locator(".is-working")).toBeVisible();
  await expect(page.locator(".life-ghost")).toBeVisible();
  await page.locator('.react-flow__node[data-id="node:e"]').click();
  await expect(page.getByText("机械审计失败")).toBeVisible();
  await page.screenshot({ path: "test-results/map-life-states.png" });
});


test("starts a workflow directly from a node", async ({ page }) => {
  let request;
  await mockMap(page);
  await page.route(/\/api\/v1\/projects\/project%3Atest\/workflows/, async (route) => {
    request = route.request().postDataJSON();
    await route.fulfill({ status: 201, json: { id: "workflow:new", ...request } });
  });
  await page.goto("/map");
  await page.locator('.react-flow__node[data-id="node:d"]').getByRole("button", { name: "从方向发起工作流" }).click();
  await expect.poll(() => request?.kind).toBe("plan-execute-review-reflect");
  expect(request.node_id).toBe("node:d");
});


test("keeps node chat IME-safe", async ({ page }) => {
  let sends = 0;
  await mockMap(page);
  await page.route(/\/api\/v1\/projects\/project%3Atest\/messages/, (route) => {
    if (route.request().method() === "POST") sends += 1;
    return route.fulfill({ status: route.request().method() === "POST" ? 201 : 200, json: route.request().method() === "POST" ? { id: 1, role: "assistant", content: "继续" } : [] });
  });
  await page.goto("/map");
  const input = page.getByLabel("节点消息");
  await input.fill("分析这个节点");
  await input.dispatchEvent("keydown", { key: "Enter", isComposing: true });
  await page.waitForTimeout(200);
  expect(sends).toBe(0);
  await input.press("Enter");
  await expect.poll(() => sends).toBe(1);
});


test("keeps the map usable on mobile", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockMap(page);
  await page.goto("/map");
  await expect(page.getByText("研究地图")).toBeVisible();
  await expect(page.locator(".graph-canvas")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await page.screenshot({ path: "test-results/map-mobile.png", fullPage: true });
});
