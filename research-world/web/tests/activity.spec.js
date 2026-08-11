import { expect, test } from "@playwright/test";

const IDS = { run: "run:test", generation: "generation:test", attempt: "attempt:test" };


function activityFixture() {
  const events = Array.from({ length: 189 }, (_, index) => ({ event_id: index + 1, run_id: IDS.run, generation_id: IDS.generation, attempt_id: IDS.attempt, actor: "producer", type: index === 2 ? "tool_call" : "research_step", time: `2026-08-12T00:00:${String(index % 60).padStart(2, "0")}Z`, entity: { type: "step", id: `step:${index}` }, payload: { message: `Recorded step ${index + 1}` } }));
  const run = { id: IDS.run, status: "completed", created_at: events[0].time, events };
  const job = { id: IDS.attempt, generation_id: IDS.generation, actor: "producer", status: "completed", created_at: events[0].time, completed_at: events.at(-1).time };
  return { events, run, job };
}


function traceFixture() {
  const base = { run_id: "trace:test", model_name: "qwen3.7-flash", workspace_root: "/workspace" };
  const records = [{ ...base, event_index: 1, turn_index: 0, timestamp: "2026-08-12T00:00:00Z", role: "user", text: "Research question", payload: {} }, { ...base, event_index: 2, turn_index: 1, timestamp: "2026-08-12T00:00:02Z", role: "assistant", text: "Evidence reviewed", payload: { response: { finish_reason: "stop", usage: { prompt_tokens: 1200, completion_tokens: 200, total_tokens: 1400 } } } }];
  return [{ attempt_id: IDS.attempt, actor: "producer", generation_id: IDS.generation, content: { output: {}, trace: [{ name: "trace.jsonl", jsonl: records.map((record) => JSON.stringify(record)).join("\n") }] } }];
}


async function mockActivity(page) {
  const { run, job } = activityFixture();
  await page.route(/\/api\/v1\/runs$/, (route) => route.fulfill({ json: [run] }));
  await page.route(/\/api\/v1\/runs\/run%3Atest$/, (route) => route.fulfill({ json: run }));
  await page.route(/\/wire$/, (route) => route.fulfill({ json: traceFixture() }));
  await page.route(/\/context$/, (route) => route.fulfill({ json: [{ attempt_id: IDS.attempt, actor: "producer", content: { messages: [{ role: "user", content: "Research question" }] } }] }));
  await page.route(/\/agents-jobs$/, (route) => route.fulfill({ json: [job] }));
  await page.route(/\/events\?follow=true$/, (route) => route.fulfill({ status: 200, contentType: "text/event-stream", body: ": ready\n\n" }));
}


async function openActivity(page, viewport) {
  await mockActivity(page);
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
  await expect(page.getByText("Turn 1").first()).toBeVisible();
  await expect(page.getByText(/tokens · context/).first()).toBeVisible();
  await assertViews(page);
  await assertNoPageOverflow(page);
  expect(errors).toEqual([]);
  await page.screenshot({ path: "test-results/activity-desktop.png" });
});


test("keeps all activity views usable on mobile", async ({ page }) => {
  await openActivity(page, { width: 390, height: 844 });
  await assertViews(page);
  await assertNoPageOverflow(page);
  await page.screenshot({ path: "test-results/activity-mobile.png" });
});
