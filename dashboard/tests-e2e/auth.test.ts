import { test, expect } from '@playwright/test';

const localCloudBaseUrl = process.env.BASE_URL || 'http://localhost:8000';

test('Login', async ({ page }) => {
    await page.goto(`${localCloudBaseUrl}/dashboard/login`);
    await page.getByRole('textbox', { name: 'Email (required)' }).fill('Administrator');
    await page.getByRole('button', { name: 'Continue with password' }).click();
    await page.getByRole('textbox', { name: 'Password (required)' }).fill('admin');
    await page.getByRole('button', { name: 'Log In' }).click();
    await expect(page).toHaveURL(/\/dashboard\/sites$/);
});