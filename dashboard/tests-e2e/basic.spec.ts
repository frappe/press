import { test, expect } from '@playwright/test';

console.log('E2E Basic Test');
console.log(process.env);

test('Test Login', async ({ page }) => {
  await page.goto('http://savetheplanet.earth:8001/dashboard/login');
  await page.locator('#scrollContainer div').filter({ hasText: 'Log in to your accountGet' }).nth(2).click({
    button: 'right'
  });
  await page.getByRole('textbox', { name: 'Email (required)' }).fill('Administrator');
  await page.getByRole('button', { name: 'Continue with password' }).click();
  await page.getByRole('textbox', { name: 'Password (required)' }).fill('abc123');
  await page.getByRole('button', { name: 'Log In' }).click();
  await expect(page).toHaveURL('http://savetheplanet.earth:8001/dashboard/');
  await page.getByRole('button', { name: 'New Site' }).click();
});

test('Test Logout', async ({ page }) => {});