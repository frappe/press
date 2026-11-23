import type { Page } from '@playwright/test';
import { expect, test } from './coverage.fixture';
import mockResponse from '../../mocks/sites/get_list.json' assert { type: 'json' };

// `Site.get_list_query` drops sites in an Archived region, so the dashboard never
// receives them. These cover what the customer is left with.

const respondWithSites = (page: Page, sites: unknown[]) =>
  page.route(/\/api\/method\/press\.api\.client\.get_list/, async route => {
    const doctype = route.request().postDataJSON()?.doctype;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ message: doctype === 'Site' ? sites : [] }),
    });
  });

test('A team whose sites are all in an archived region sees the empty state', async ({
  page,
}) => {
  await respondWithSites(page, []);

  await page.goto('/dashboard/sites');

  await expect(page.getByPlaceholder('Search sites')).toBeVisible();
  await expect(page.getByText('No sites')).toBeVisible();
});

test('The sites an archived region leaves behind still list normally', async ({
  page,
}) => {
  await respondWithSites(page, mockResponse.message);

  await page.goto('/dashboard/sites');

  for (const site of mockResponse.message) {
    await expect(page.getByText(site.name)).toBeVisible();
  }
});
