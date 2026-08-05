import type { Page, Route } from '@playwright/test'
import { expect, test } from './coverage.fixture'

const SERVER_NAME = 'f1-mumbai.frappe.cloud'
const SITE_NAME = 'test-disk-full.fc.frappe.dev'
const BANNER_TITLE = 'Server is out of disk space'
const BANNER_MESSAGE =
	'Sites on this server may stop responding until space is freed up. Add a storage add-on or drop old backups and logs.'

// What press.api.account.get_user_banners returns for a server whose disk is full
const diskFullBanner = {
	name: 'banner-disk-full',
	type: 'Error',
	title: BANNER_TITLE,
	message: BANNER_MESSAGE,
	type_of_scope: 'Server',
	help_url: 'https://docs.frappe.io/cloud/storage-addons',
	has_action: 0,
	is_dismissible: 0,
	is_global: 0,
	server: [SERVER_NAME],
	site: [],
	cluster: [],
}

const siteMock = {
	message: {
		name: SITE_NAME,
		status: 'Active',
		server: SERVER_NAME,
		cluster: 'Mumbai',
		version: 'Version 15',
		eol_versions: [],
		is_monitoring_disabled: 0,
		// current_plan null prevents the upsell banners from appearing
		current_plan: null,
		group_public: 0,
	},
}

const serverMock = {
	message: {
		name: SERVER_NAME,
		title: 'Test Server',
		status: 'Active',
		cluster: 'Mumbai',
		team: 'test@example.com',
		database_server: 'm1-mumbai.frappe.cloud',
	},
}

async function mockDashboard(page: Page, banners: object[]) {
	await page.route(
		/\/api\/method\/press\.api\.account\.get_user_banners/,
		async (route: Route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ message: banners }),
			})
		},
	)

	await page.route(
		/\/api\/method\/press\.api\.client\.get\b/,
		async (route: Route) => {
			const doctype = new URL(route.request().url()).searchParams.get('doctype')
			if (doctype === 'Site') {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify(siteMock),
				})
			} else if (doctype === 'Server') {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify(serverMock),
				})
			} else {
				await route.continue()
			}
		},
	)
}

test('shows the disk full banner on the server dashboard', async ({ page }) => {
	await mockDashboard(page, [diskFullBanner])

	await page.goto(`/dashboard/servers/${SERVER_NAME}/overview`)

	await expect(page.getByText(BANNER_MESSAGE)).toBeVisible({ timeout: 10000 })
})

test('shows the disk full banner on a site hosted on that server', async ({
	page,
}) => {
	await mockDashboard(page, [diskFullBanner])

	await page.goto(`/dashboard/sites/${SITE_NAME}/overview`)

	// The banner is scoped to the server, not the site
	await expect(page.getByText(BANNER_MESSAGE)).toBeVisible({ timeout: 10000 })
})

test('hides the disk full banner once the server has space again', async ({
	page,
}) => {
	await mockDashboard(page, [])

	await page.goto(`/dashboard/sites/${SITE_NAME}/overview`)

	await expect(page.getByText('Current Plan')).toBeVisible({ timeout: 10000 })
	await expect(page.getByText(BANNER_MESSAGE)).not.toBeVisible()
})
