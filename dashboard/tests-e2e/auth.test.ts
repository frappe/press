import { expect, test } from '@playwright/test';

const localCloudBaseUrl = process.env.BASE_URL || 'http://localhost:8000';
const userEmail = process.env.PRESS_ADMIN_USER_EMAIL || 'Frappe';

test('Login', async ({ page }) => {
    await page.goto(`${localCloudBaseUrl}/dashboard/login`);
    await page.getByRole('textbox', { name: 'Email (required)' }).click();
    await page.getByRole('textbox', { name: 'Email (required)' }).fill(userEmail);
    await page.getByRole('button', { name: 'Send verification code' }).click();
    await page.getByRole('textbox', { name: 'Verification code (required)' }).click();
    await page.getByRole('textbox', { name: 'Verification code (required)' }).fill('111111');
    await page.getByRole('button', { name: 'Submit verification code' }).click();
    
    const url = new URL(page.url());
    expect(url.pathname).toBe("/dashboard/welcome");
});