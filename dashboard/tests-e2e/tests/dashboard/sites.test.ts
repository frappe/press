import { expect, test } from './coverage.fixture';
import mockResponse from '../../mocks/sites/get_list.json' assert { type: 'json' };

test('Ensure sites are visible in the list', async ({ page }) => {
  await page.route('*/**/api/method/press.api.client.get_list', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(mockResponse),
    });
  });

  await page.goto('/dashboard/sites');

  for (const site of mockResponse.message) {
    await expect(page.getByText(site.name)).toBeVisible();
  }
});
