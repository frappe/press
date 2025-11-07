import { test, expect } from '@playwright/test';

const localCloudBaseUrl = new URL(process.env.BASE_URL || 'http://localhost:8000').hostname;

test('Login', async ({ page }) => {
    await page.goto(`${localCloudBaseUrl}/dashboard/login`);
    await page.locator('#scrollContainer div').filter({ hasText: 'Log in to your account' }).nth(2).click({
      button: 'right'
    });
    await page.getByRole('textbox', { name: 'Email (required)' }).fill('Administrator');
    await page.getByRole('button', { name: 'Continue with password' }).click();
    await page.getByRole('textbox', { name: 'Password (required)' }).fill('admin');
    await page.getByRole('button', { name: 'Log In' }).click();
    await expect(page).toHaveURL(`**/dashboard/sites`);
});

export { test };