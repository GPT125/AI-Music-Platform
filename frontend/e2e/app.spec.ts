import { test, expect } from "@playwright/test";

test("renders login screen", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Private beta login")).toBeVisible();
  await expect(page.getByRole("button", { name: /sign in/i })).toBeVisible();
});

