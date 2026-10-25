import { test, expect } from "@playwright/test";

test("board detail renders whiteboard shell", async ({ page }) => {
  await page.goto("/boards/example");
  await expect(page.getByText("Whiteboard Workspace")).toBeVisible();
});
