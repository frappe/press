import type { Route } from '@playwright/test'
import { expect, test } from './coverage.fixture'

const SITE_NAME = 'test-stale.fc.frappe.dev'
const BANNER_TEXT = /This site runs Frappe Framework code that is \d+ days old/

function daysAgo(days: number): string {
	const date = new Date(Date.now() - days * 24 * 60 * 60 * 1000)
	return date.toISOString().slice(0, 19).replace('T', ' ')
}

function siteMock(frappeUpdatedOn: string) {
	return {
		message: {
			name: SITE_NAME,
			status: 'Active',
			// current_plan null prevents the upsell banner from appearing
			current_plan: null,
			group_public: 0,
			eol_versions: [],
			frappe_updated_on: frappeUpdatedOn,
		},
	}
}

async function mockSite(
	page: Parameters<typeof test>[1]['page'],
	frappeUpdatedOn: string,
) {
	await page.route(
		/\/api\/method\/press\.api\.client\.get\b/,
		async (route: Route) => {
			const url = new URL(route.request().url())
			if (url.searchParams.get('doctype') === 'Site') {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify(siteMock(frappeUpdatedOn)),
				})
			} else {
				await route.continue()
			}
		},
	)

	await page.route(
		/\/api\/method\/press\.api\.client\.get_list/,
		async (route: Route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ message: [] }),
			})
		},
	)
}

test('shows the update reminder when the deployed frappe commit is over 30 days old', async ({
	page,
}) => {
	await mockSite(page, daysAgo(45))

	await page.goto(`/dashboard/sites/${SITE_NAME}/updates`)

	await expect(page.getByText(BANNER_TEXT)).toBeVisible({ timeout: 10000 })
})

test('keeps the update reminder visible across tabs', async ({ page }) => {
	await mockSite(page, daysAgo(45))

	await page.goto(`/dashboard/sites/${SITE_NAME}/updates`)
	await expect(page.getByText(BANNER_TEXT)).toBeVisible({ timeout: 10000 })

	// The tab bar exposes role=tab, not link: the router-link inside each tab is
	// a presentational child of the tab and never reaches the accessibility tree.
	await page.getByRole('tab', { name: 'Domains' }).click()
	await expect(page).toHaveURL(/\/domains$/)
	await expect(page.getByText(BANNER_TEXT)).toBeVisible()
})

test('hides the update reminder when the deployed frappe commit is recent', async ({
	page,
}) => {
	await mockSite(page, daysAgo(5))

	await page.goto(`/dashboard/sites/${SITE_NAME}/updates`)

	// Wait for the page to settle before asserting an absence
	await expect(page.getByRole('tab', { name: 'Domains' })).toBeVisible({
		timeout: 10000,
	})
	await expect(page.getByText(BANNER_TEXT)).not.toBeVisible()
})
