import { test, expect } from "@playwright/test";

test("assistant sidebar placeholder is visible", async ({ page }) => {
  await page.goto("/boards/example");
  await expect(page.getByRole("heading", { name: "New Agent" })).toBeVisible();
});
