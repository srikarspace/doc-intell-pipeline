// One sample from start to end: stream, rows, PDF, highlights, review, undo, Passed, Copy JSON.
// The stream is a stored real answer (no model call). Everything else is the real API and the built UI.

import { expect, type Page, test } from "@playwright/test";
import { readFileSync } from "node:fs";

type Event = { event: string; data: unknown };

/** Answer POST /v1/extract/stream with a stored stream, in the same SSE text the API sends. */
async function replay(page: Page, sample: string) {
  const file = new URL(`../src/fixtures/${sample}-stream.json`, import.meta.url);
  const events: Event[] = JSON.parse(readFileSync(file, "utf8"));
  const body = events.map((e) => `event: ${e.event}\ndata: ${JSON.stringify(e.data)}\n\n`).join("");
  await page.route("**/v1/extract/stream", (route) =>
    route.fulfill({ status: 200, contentType: "text/event-stream", body }),
  );
}

const row = (page: Page, label: string) => page.getByRole("button", { name: new RegExp(`^${label}`) });

test("review both flags of Kubient until it passes, then undo one", async ({ page, context }) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await replay(page, "kubient");
  await page.goto("/");
  await page.getByRole("button", { name: /^Kubient: master services agreement Service/ }).click();

  const pill = page.getByRole("status");
  await expect(pill).toContainText("2 issues found");
  await expect(page.locator("aside canvas").first()).toBeVisible(); // the PDF is drawn

  // The first flagged field opens by itself, with its review card.
  await expect(page.getByRole("button", { name: "Accept" })).toBeVisible();

  // A found field: its quote gets a box on the PDF.
  await row(page, "Parties").click();
  await expect(page.locator('[data-mark="quote"]').first()).toBeVisible();

  // Accept Non-compete. The next flag (Renewal term) opens, with its evidence line in amber.
  await row(page, "Non-compete").click();
  await page.getByRole("button", { name: "Accept" }).click();
  await expect(page.locator('[data-mark="evidence"]').first()).toBeVisible();
  await page.getByRole("button", { name: "Keep “not found”" }).click();
  await expect(pill).toContainText("Passed");
  await expect(pill).toContainText("2 reviewed");

  // Undo the last review: the issue comes back.
  await page.getByRole("button", { name: "Undo" }).click();
  await expect(pill).toContainText("1 issue found");

  // Copy JSON gives the reviewed answer, with each review next to its field.
  await page.getByRole("button", { name: "Copy JSON" }).click();
  const json = JSON.parse(await page.evaluate(() => navigator.clipboard.readText()));
  expect(json.fields.non_compete.review.action).toBe("accept");
  expect(json.fields.renewal_term.review).toBeNull();
});

test("an answer with no flags passes at once", async ({ page }) => {
  await replay(page, "ecoscience");
  await page.goto("/");
  await page.getByRole("button", { name: /^EcoScience/ }).click();
  await expect(page.getByRole("status")).toHaveText("Passed");
  await expect(page.locator("aside canvas").first()).toBeVisible();
});
