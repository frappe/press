import type { Page } from '@playwright/test';
import { expect, test } from './coverage.fixture';

// `Server.get_list_query`, `Bench.get_list_query` and `ReleaseGroup.get_list_query`
// drop archived regions, so the dashboard never receives them. These cover what
// the customer is left with on the Benches and Servers pages.

const respondWith = (page: Page, doctypes: Record<string, unknown[]>) =>
  page.route(/\/api\/method\/press\.api\.client\.get_list/, async route => {
    const doctype = route.request().postDataJSON()?.doctype;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ message: doctypes[doctype] ?? [] }),
    });
  });

const mumbaiGroup = {
  name: 'bench-0001',
  title: 'Acme Production',
  version: 'Version 15',
  active_benches: 1,
  site_count: 2,
  server: 'f1.frappe.cloud',
  server_title: 'Mumbai App Server',
  server_provider: 'AWS EC2',
  apps: [{ app: 'frappe' }, { app: 'erpnext' }],
};

const mumbaiServer = {
  name: 'f1.frappe.cloud',
  title: 'Mumbai App Server',
  status: 'Active',
  provider: 'AWS EC2',
  database_server: 'm1.frappe.cloud',
  plan_title: 'Standard',
  price_usd: 100,
  price_inr: 8000,
  cluster: 'Mumbai',
  cluster_title: 'Mumbai',
  cluster_country: 'India',
  is_unified_server: 0,
  vcpu: 4,
  memory: 8192,
  disk: 100,
};

test('A team whose bench groups were all in an archived region sees the empty state', async ({
  page,
}) => {
  await respondWith(page, { 'Release Group': [] });

  await page.goto('/dashboard/groups');

  await expect(page.getByText('No benches')).toBeVisible();
});

test('Bench groups outside an archived region still list', async ({ page }) => {
  await respondWith(page, { 'Release Group': [mumbaiGroup] });

  await page.goto('/dashboard/groups');

  await expect(page.getByText(mumbaiGroup.title)).toBeVisible();
});

test('Servers outside an archived region still list', async ({ page }) => {
  await respondWith(page, { Server: [mumbaiServer] });

  await page.goto('/dashboard/servers');

  await expect(page.getByText(mumbaiServer.title)).toBeVisible();
});

test('A team whose servers were all in an archived region sees none listed', async ({
  page,
}) => {
  await respondWith(page, { Server: [] });

  await page.goto('/dashboard/servers');

  await expect(page.getByRole('button', { name: 'New Server' })).toBeVisible();
  await expect(page.getByText('Mumbai App Server')).toHaveCount(0);
});
