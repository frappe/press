import { test, expect } from '@playwright/test';

test('hello world', async ({ page }) => {
  console.log('Playwright CI!');
  expect(true).toBe(true);
});