import { test, expect } from "@playwright/test";

test("renders login screen", async ({ page }) => {
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await expect(page.getByText("Practice with an orchestra that follows you")).toBeVisible();
  await expect(page.getByRole("button", { name: "Sign in or sign up with Google" })).toBeVisible();
});
