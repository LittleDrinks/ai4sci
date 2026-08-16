import { expect, test } from "@playwright/test";


function node(id, kind, state = {}) {
  return { id, project_id: "project:test", parent_id: null, lineage_id: `lineage:${id}`,
    kind, payload: { text: `${kind} node` }, life_state: "admitted", direction_status: kind === "direction" ? "proposed" : null,
    working: 0, rejection_reason: null, rebuttal: null, created_at: "2026-08-16T00:00:00Z", updated_at: "2026-08-16T00:00:00Z", ...state };
}


function fixture() {
  const nodes = [node("node:q", "question"), node("node:s", "source"),
    node("node:d", "direction", { parent_id: "node:q" }), node("node:e", "experiment", { parent_id: "node:d" })];
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
  await expect(page.locator(".react-flow__edge")).toHaveCount(3);
  await expect(page.locator(".node-run")).toHaveCount(0);
  await expect(page.locator('.react-flow__node[data-id="node:q"] footer')).not.toContainText("0");
  await expect(page.getByRole("img", { name: "问题图标" })).toBeVisible();
  expect(await page.locator(".hidden-handle").first().evaluate((element) => getComputedStyle(element).opacity)).toBe("0");
});


test("keeps large graph edges initialized", async ({ page }) => {
  const body = fixture();
  body.nodes = [body.nodes[0], ...Array.from({ length: 45 }, (_, index) => node(`node:d${index}`, "direction", { parent_id: "node:q" }))];
  body.edges = [];
  await mockMap(page, body);
  await page.goto("/map");
  await expect(page.locator(".signal-edge")).toHaveCount(45);
  await expect(page.locator(".signal-flow-path")).toHaveCount(45);
});


test("animates visible signal paths along graph relations", async ({ page }) => {
  await mockMap(page);
  await page.goto("/map");
  const paths = page.locator(".signal-flow-path");
  await expect(paths).not.toHaveCount(0);
  expect(await paths.count()).toBe(await page.locator(".signal-edge").count());
  expect(await paths.first().evaluate((element) => getComputedStyle(element).display)).not.toBe("none");
  await expect(paths.first().locator("animate")).toHaveAttribute("repeatCount", "indefinite");
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


test("starts a workflow from the inspector and opens its activity", async ({ page }) => {
  let request;
  await mockMap(page);
  await page.route(/\/api\/v1\/projects\/project%3Atest\/workflows/, async (route) => {
    request = route.request().postDataJSON();
    await route.fulfill({ status: 201, json: { id: "workflow:new", ...request } });
  });
  await page.goto("/map");
  await page.locator('.react-flow__node[data-id="node:d"]').click();
  await page.getByRole("button", { name: "发起工作流", exact: true }).click();
  await expect.poll(() => request?.kind).toBe("plan-execute-review-reflect");
  expect(request.node_id).toBe("node:d");
  await expect(page).toHaveURL(/\/activity\?workflow=workflow%3Anew$/);
});


test("opens the workflow associated with an experiment", async ({ page }) => {
  const body = fixture();
  body.workflows = [{ id: "workflow:experiment", project_id: "project:test", node_id: "node:d", lineage_id: "lineage:node:d",
    kind: "plan-execute-review-reflect", stage: "execute", status: "waiting_human", payload: { experiment_id: "node:e" },
    auto: 0, created_at: "2026-08-16T00:00:00Z", updated_at: "2026-08-16T00:00:00Z", steps: [], events: [] }];
  await mockMap(page, body);
  await page.goto("/map");
  await page.locator('.react-flow__node[data-id="node:e"]').click();
  await page.getByRole("button", { name: "继续工作流" }).click();
  await expect(page).toHaveURL(/\/activity\?workflow=workflow%3Aexperiment$/);
});


test("starts experiment reflection from the inspector", async ({ page }) => {
  let request;
  await mockMap(page);
  await page.route(/\/api\/v1\/projects\/project%3Atest\/workflows/, async (route) => {
    request = route.request().postDataJSON();
    await route.fulfill({ status: 201, json: { id: "workflow:reflection", ...request } });
  });
  await page.goto("/map");
  await page.locator('.react-flow__node[data-id="node:e"]').click();
  await page.getByRole("button", { name: "反思实验" }).click();
  await expect.poll(() => request?.payload?.mode).toBe("reflect");
  expect(request).toMatchObject({ node_id: "node:e", kind: "brainstorm" });
  await expect(page).toHaveURL(/\/activity\?workflow=workflow%3Areflection$/);
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
