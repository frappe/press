import type { Page, Route } from '@playwright/test'
import { expect, test } from './coverage.fixture'

const SITE_NAME = 'test-compute.fc.frappe.dev'
const COMPUTE_HOURS_PER_DAY = 10

const NEAR_LIMIT_BANNER =
	'This site has used 85% of the compute time its plan includes for today. At 100%, requests start to fail.'
const OVER_LIMIT_BANNER =
	'This site has used all the compute time its plan includes for today. Some requests will fail until the count resets.'
const RESET_TEXT = 'The count resets in 5 hours.'

// group_public 0 keeps the shared bench upsell banner out of the way
const site = {
	name: SITE_NAME,
	status: 'Active',
	server: 'f1-mumbai.frappe.cloud',
	cluster: 'Mumbai',
	version: 'Version 15',
	eol_versions: [],
	is_monitoring_disabled: 0,
	is_dedicated_server: 0,
	group_public: 0,
	current_plan: {
		name: 'Standard',
		cpu_time_per_day: COMPUTE_HOURS_PER_DAY,
		max_storage_usage: 20480,
		max_database_usage: 10240,
		private_benches: 1,
		price_inr: 750,
		price_usd: 10,
	},
}

async function mockSite(page: Page, overrides: Record<string, unknown> = {}) {
	await page.route(
		/\/api\/method\/press\.api\.client\.get\b/,
		async (route: Route) => {
			const url = new URL(route.request().url())
			if (url.searchParams.get('doctype') !== 'Site') return route.continue()

			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ message: { ...site, ...overrides } }),
			})
		},
	)
}

// `run_doc_method` responses carry `docs`, and frappe-ui then hands the whole
// response to the resource. SiteOverview reads it as `data.message`.
async function mockCurrentUsage(page: Page, computeHoursUsed: number) {
	await page.route(
		/\/api\/method\/press\.api\.client\.run_doc_method\b/,
		async (route: Route) => {
			if (route.request().postDataJSON()?.method !== 'get_current_usage') {
				return route.continue()
			}

			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					message: {
						cpu: computeHoursUsed,
						storage: 0,
						database: 0,
						hours_until_cpu_usage_resets: 5,
					},
					docs: [{}],
				}),
			})
		},
	)
}

test('warns on the site overview once the site reaches 80% of its daily compute', async ({
	page,
}) => {
	await mockSite(page)
	await mockCurrentUsage(page, 8.5)

	await page.goto(`/dashboard/sites/${SITE_NAME}/overview`)

	await expect(page.getByText(NEAR_LIMIT_BANNER)).toBeVisible({
		timeout: 10000,
	})
	await expect(page.getByText(RESET_TEXT)).toBeVisible()
})

test('tells the user requests fail once the site used all of its daily compute', async ({
	page,
}) => {
	await mockSite(page)
	await mockCurrentUsage(page, 10.2)

	await page.goto(`/dashboard/sites/${SITE_NAME}/overview`)

	await expect(page.getByText(OVER_LIMIT_BANNER)).toBeVisible({
		timeout: 10000,
	})
})

test('shows no warning while the site is below 80% of its daily compute', async ({
	page,
}) => {
	await mockSite(page)
	await mockCurrentUsage(page, 5)

	await page.goto(`/dashboard/sites/${SITE_NAME}/overview`)

	await expect(page.getByText('Current Plan')).toBeVisible({ timeout: 10000 })
	await expect(page.getByText('of the compute time its plan')).not.toBeVisible()
})

test('shows no warning for a site on a dedicated server, which has no daily limit', async ({
	page,
}) => {
	await mockSite(page, { is_dedicated_server: 1 })
	await mockCurrentUsage(page, 10.2)

	await page.goto(`/dashboard/sites/${SITE_NAME}/overview`)

	await expect(page.getByText('Current Plan')).toBeVisible({ timeout: 10000 })
	await expect(
		page.getByText('the compute time its plan includes'),
	).not.toBeVisible()
})
