import type { Page, Route } from '@playwright/test'
import { expect, test } from './coverage.fixture'

const SERVER_NAME = 'f1-mumbai.frappe.cloud'
const SITE_NAME = 'test-disk-full.fc.frappe.dev'
const SITE_BANNER =
	"This site's server is out of disk space. The site may stop responding until space is freed up."
const SERVER_BANNER =
	'This server is out of disk space. Sites on it may stop responding until space is freed up.'

const site = {
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
}

const server = {
	name: SERVER_NAME,
	title: 'Test Server',
	status: 'Active',
	cluster: 'Mumbai',
	team: 'test@example.com',
	database_server: 'm1-mumbai.frappe.cloud',
}

// is_server_disk_full is set by Site.get_doc / Server.get_doc from the disk full alerts
async function mockDashboard(page: Page, isServerDiskFull: 0 | 1) {
	await page.route(
		/\/api\/method\/press\.api\.client\.get\b/,
		async (route: Route) => {
			const doctype = new URL(route.request().url()).searchParams.get('doctype')
			const doc =
				doctype === 'Site' ? site : doctype === 'Server' ? server : null

			if (!doc) return route.continue()

			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					message: { ...doc, is_server_disk_full: isServerDiskFull },
				}),
			})
		},
	)
}

test('shows the disk full banner on the server dashboard', async ({ page }) => {
	await mockDashboard(page, 1)

	await page.goto(`/dashboard/servers/${SERVER_NAME}/overview`)

	await expect(page.getByText(SERVER_BANNER)).toBeVisible({ timeout: 10000 })
})

test('shows the disk full banner on a site hosted on that server', async ({
	page,
}) => {
	await mockDashboard(page, 1)

	await page.goto(`/dashboard/sites/${SITE_NAME}/overview`)

	await expect(page.getByText(SITE_BANNER)).toBeVisible({ timeout: 10000 })
})

test('hides the disk full banner once the server has space again', async ({
	page,
}) => {
	await mockDashboard(page, 0)

	await page.goto(`/dashboard/sites/${SITE_NAME}/overview`)

	await expect(page.getByText('Current Plan')).toBeVisible({ timeout: 10000 })
	await expect(page.getByText(SITE_BANNER)).not.toBeVisible()
})
