import { expect, test } from '@playwright/test';

const localCloudBaseUrl = process.env.BASE_URL || 'http://localhost:8000';
const userEmail: string = process.env.PRESS_ADMIN_USER_EMAIL!;
const userPassword: string = process.env.PRESS_ADMIN_USER_PASSWORD!;

test('Login', async ({ page }) => {
    await page.goto(`${localCloudBaseUrl}/dashboard/login`);
    await page.getByRole('textbox', { name: 'Email (required)' }).click();
    await page.getByRole('textbox', { name: 'Email (required)' }).fill(userEmail);
    await page.getByRole('button', { name: 'Continue with password' }).click();
    await page.getByRole('textbox', { name: 'Password (required)' }).click();
    await page.getByRole('textbox', { name: 'Password (required)' }).fill(userPassword);
    await page.getByRole('button', { name: 'Log In' }).click();

    const url = new URL(page.url());
    expect(url.pathname).toBe("/dashboard/sites");
});