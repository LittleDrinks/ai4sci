import { expect, test } from "@playwright/test";


function node(id, kind, state = {}) {
  return { id, project_id: "project:test", parent_id: null, lineage_id: `lineage:${id}`, kind, payload: { text: `${kind} 节点` },
    life_state: "admitted", direction_status: kind === "direction" ? "proposed" : null, working: 0, rejection_reason: null, rebuttal: null,
    created_at: "2026-08-16T00:00:00Z", updated_at: "2026-08-16T00:00:00Z", ...state };
}


function fixture(nodes = [node("node:q", "question"), node("node:d", "direction")]) {
  return { projects: [{ id: "project:test", title: "测试项目", question: "如何验证？", auto: 0, created_at: "2026-08-16T00:00:00Z" }], active_project_id: "project:test",
    nodes, edges: [], workflows: [], slots: [{ index: 1, workflow: null }, { index: 2, workflow: null }] };
}


async function mockChat(page, body = fixture()) {
  await page.route(/\/api\/v1\/bootstrap/, (route) => route.fulfill({ json: body }));
  await page.route(/\/api\/v1\/projects\/project%3Atest\/messages/, (route) => {
    if (route.request().method() === "GET") return route.fulfill({ json: [{ id: 1, role: "assistant", content: "已带入问题上下文" }] });
    return route.fulfill({ status: 201, json: { id: 2, role: "assistant", content: "先生成并筛选多个研究方向。", actions: ["brainstorm"] } });
  });
}


test("sends a message with the selected node context", async ({ page }) => {
  let request;
  await mockChat(page);
  await page.route(/\/api\/v1\/projects\/project%3Atest\/messages/, (route) => {
    if (route.request().method() === "GET") return route.fulfill({ json: [{ id: 1, role: "assistant", content: "已带入问题上下文" }] });
    request = route.request().postDataJSON();
    return route.fulfill({ status: 201, json: { id: 2, role: "assistant", content: "先生成并筛选多个研究方向。" } });
  });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/chat");
  await expect(page.getByText("已带入问题上下文")).toBeVisible();
  await page.screenshot({ path: "test-results/chat-desktop.png" });
  await page.getByLabel("消息").fill("下一步做什么？");
  await page.getByRole("button", { name: "发送" }).click();
  await expect(page.getByText("先生成并筛选多个研究方向。")).toBeVisible();
  expect(request).toEqual({ node_id: "node:q", message: "下一步做什么？" });
});


test("maps reflection to a brainstorm workflow", async ({ page }) => {
  let request;
  const direction = node("node:d", "direction", { direction_status: "supported" });
  await mockChat(page, fixture([direction]));
  await page.route(/\/api\/v1\/projects\/project%3Atest\/workflows/, (route) => {
    request = route.request().postDataJSON();
    return route.fulfill({ status: 201, json: { id: "workflow:new", ...request } });
  });
  await page.goto("/chat");
  await page.getByRole("button", { name: "反思证据" }).click();
  await expect.poll(() => request?.kind).toBe("brainstorm");
  expect(request.node_id).toBe("node:d");
});


test("materializes the draft as a direction and clears the thread", async ({ page }) => {
  let request;
  await mockChat(page);
  await page.route(/\/api\/v1\/projects\/project%3Atest\/drafts\/materialize/, (route) => {
    request = route.request().postDataJSON();
    return route.fulfill({ status: 201, json: node("node:new", "direction") });
  });
  await page.goto("/chat");
  await page.getByLabel("消息").fill("检验轨道共振的长期稳定性");
  await page.getByRole("button", { name: "沉淀方向" }).click();
  await expect.poll(() => request?.kind).toBe("direction");
  expect(request.payload.text).toBe("检验轨道共振的长期稳定性");
  await expect(page.getByText("当前节点尚无对话草稿")).toBeVisible();
});


test("keeps the manager chat IME-safe and readable on mobile", async ({ page }) => {
  let sends = 0;
  await page.setViewportSize({ width: 390, height: 844 });
  await mockChat(page);
  await page.route(/\/api\/v1\/projects\/project%3Atest\/messages/, (route) => {
    if (route.request().method() === "POST") sends += 1;
    return route.fulfill({ status: route.request().method() === "POST" ? 201 : 200, json: route.request().method() === "POST" ? { id: 2, role: "assistant", content: "继续" } : [] });
  });
  await page.goto("/chat");
  await expect(page.getByRole("button", { name: "生成方向" })).toBeVisible();
  await page.screenshot({ path: "test-results/chat-mobile.png", fullPage: true });
  const input = page.getByLabel("消息");
  await input.fill("分析当前节点");
  await input.dispatchEvent("keydown", { key: "Enter", isComposing: true });
  await page.waitForTimeout(150);
  expect(sends).toBe(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
});
