import { test, expect } from "@playwright/test";

test("boards page is reachable", async ({ page }) => {
  await page.goto("/boards");
  await expect(page.getByRole("heading", { name: "Boards" })).toBeVisible();
});
