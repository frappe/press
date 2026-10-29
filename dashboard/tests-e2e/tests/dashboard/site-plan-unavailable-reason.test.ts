import type { Page, Route } from '@playwright/test'
import { expect, test } from './coverage.fixture'

const SITE_NAME = 'test-plan-picker.fc.frappe.dev'

const basePlan = {
	price_inr: 0,
	cpu_time_per_day: 1,
	max_storage_usage: 1024,
	max_database_usage: 1024,
	dedicated_server_plan: 0,
	restrict_based_on_dedicated_server_plan: 0,
	cloud_providers: [],
	clusters: [],
	allowed_apps: [],
	bench_versions: [],
	restricted_plan: false,
}

// Only the $25 plan allows a private bench
const plans = [
	{
		...basePlan,
		name: 'USD 5',
		plan_title: '$5',
		price_usd: 5,
		private_benches: 0,
	},
	{
		...basePlan,
		name: 'USD 25',
		plan_title: '$25',
		price_usd: 25,
		private_benches: 1,
	},
]

function site(groupPublic: 0 | 1) {
	return {
		name: SITE_NAME,
		status: 'Active',
		server: 'f1-mumbai.frappe.cloud',
		server_provider: 'AWS EC2',
		cluster: 'Mumbai',
		version: 'Version 15',
		eol_versions: [],
		is_monitoring_disabled: 0,
		is_dedicated_server: 0,
		group_public: groupPublic,
		plan: 'USD 25',
		current_plan: { ...plans[1], is_trial_plan: 0 },
	}
}

async function mockDashboard(page: Page, groupPublic: 0 | 1) {
	await page.route(
		/\/api\/method\/press\.api\.site\.get_site_plans/,
		(route: Route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ message: plans }),
			}),
	)
	await page.route(
		/\/api\/method\/press\.api\.client\.get\b/,
		async (route: Route) => {
			const doctype = new URL(route.request().url()).searchParams.get('doctype')
			if (doctype !== 'Site') return route.continue()

			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ message: site(groupPublic) }),
			})
		},
	)
}

async function openChangePlanDialog(page: Page) {
	await page.goto(`/dashboard/sites/${SITE_NAME}/overview`)
	await page.getByRole('button', { name: 'Change', exact: true }).click()
	return page.getByRole('dialog')
}

test('shows a plan without private bench support as disabled with the reason on a private bench', async ({
	page,
}) => {
	await mockDashboard(page, 0)
	const dialog = await openChangePlanDialog(page)

	const unavailablePlan = dialog.getByRole('button', {
		name: /Not available on a private bench/,
	})
	await expect(unavailablePlan).toBeVisible({ timeout: 10000 })
	await expect(unavailablePlan).toBeDisabled()

	const availablePlan = dialog.getByRole('button', {
		name: /Private Bench & Custom Apps/,
	})
	await expect(availablePlan).toBeEnabled()
})

test('shows every plan as available on a public bench', async ({ page }) => {
	await mockDashboard(page, 1)
	const dialog = await openChangePlanDialog(page)

	await expect(
		dialog.getByRole('button', { name: /Private Bench & Custom Apps/ }),
	).toBeVisible({ timeout: 10000 })
	await expect(
		dialog.getByText('Not available on a private bench'),
	).toHaveCount(0)
	await expect(
		dialog.getByRole('button', { disabled: true, name: /compute/ }),
	).toHaveCount(0)
})
