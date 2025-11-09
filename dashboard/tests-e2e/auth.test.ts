import { test, expect } from '@playwright/test';

const localCloudBaseUrl = process.env.BASE_URL || 'http://localhost:8000';
const userEmail = process.env.PRESS_ADMIN_USER_EMAIL || 'Frappe';
const userPwd = process.env.PRESS_ADMIN_USER_PWD || 'admin';

test('Login', async ({ page }) => {
    await page.goto(`${localCloudBaseUrl}/dashboard/login`);
    await page.getByRole('textbox', { name: 'Email (required)' }).fill(userEmail);
    await page.getByRole('button', { name: 'Continue with password' }).click();
    await page.getByRole('textbox', { name: 'Password (required)' }).fill(userPwd);
    await page.getByRole('button', { name: 'Log In' }).click();
    await expect(page).toHaveURL(/\/dashboard\/welcome$/);
});