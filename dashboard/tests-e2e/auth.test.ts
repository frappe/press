import { expect, test } from '@playwright/test';

const localCloudBaseUrl = process.env.BASE_URL || 'http://localhost:8000';
const userEmail = process.env.PRESS_ADMIN_USER_EMAIL || 'playwright@example.com';

test('Login', async ({ page }) => {
    await page.goto(`${localCloudBaseUrl}/dashboard/login`);
    await page.getByRole('textbox', { name: 'Email (required)' }).click();
    await page.waitForTimeout(500);
    await page.getByRole('textbox', { name: 'Email (required)' }).fill('playwright@example.com');
    await page.waitForTimeout(500);
    await page.getByRole('button', { name: 'Continue with password' }).click();
    await page.waitForTimeout(500);
    await page.getByRole('textbox', { name: 'Password (required)' }).click();
    await page.waitForTimeout(500);
    await page.getByRole('textbox', { name: 'Password (required)' }).fill('admin');
    await page.waitForTimeout(500);
    await page.getByRole('button', { name: 'Log In' }).click();
    await page.waitForTimeout(500);

    const url = new URL(page.url());
    expect(url.pathname).toBe("/dashboard/welcome");
});