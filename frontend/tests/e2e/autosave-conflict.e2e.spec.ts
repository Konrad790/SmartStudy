import { test, expect } from "@playwright/test";

test("board page still accessible for autosave workflows", async ({ page }) => {
  await page.goto("/boards/example");
  await expect(page.getByText("Whiteboard Workspace")).toBeVisible();
});
