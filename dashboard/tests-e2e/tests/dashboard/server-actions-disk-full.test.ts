import type { Page } from '@playwright/test'
import { expect, test } from './coverage.fixture'

const APP_SERVER = 'f-test-app.frappe.cloud'
const DATABASE_SERVER = 'm-test-db.frappe.cloud'

const appServerDoc = {
	name: APP_SERVER,
	title: 'Test Server',
	status: 'Active',
	is_unified_server: 0,
	database_server: DATABASE_SERVER,
	replication_server: null,
	actions: [
		{
			action: 'Reboot server',
			description: 'Reboot the server',
			button_label: 'Reboot',
			doc_method: 'reboot',
			group: 'Server Actions',
			server_doctype: 'Server',
			server_name: APP_SERVER,
		},
		{
			action: 'Manage On-Prem Replication',
			description: 'Manage On-Prem Replication &amp; Failover',
			button_label: 'Manage',
			doc_method: 'dummy',
			group: 'Server Actions',
			server_doctype: 'Server',
			server_name: APP_SERVER,
		},
	],
}

const databaseServerDoc = {
	name: DATABASE_SERVER,
	title: 'Test Database Server',
	status: 'Active',
	actions: [
		{
			action: 'Forcefully Purge Binlogs',
			description:
				'Use this in case of <span class="text-red-600">disk full</span> issues',
			button_label: 'Purge',
			doc_method: 'purge_binlogs_forcefully',
			group: 'Database Actions',
			server_doctype: 'Database Server',
			server_name: DATABASE_SERVER,
		},
	],
}

async function mockServerDocs(page: Page) {
	await page.route(
		/\/api\/method\/press\.api\.client\.get\b/,
		async (route) => {
			const doctype = new URL(route.request().url()).searchParams.get('doctype')
			const doc =
				doctype === 'Server'
					? appServerDoc
					: doctype === 'Database Server'
						? databaseServerDoc
						: null
			if (!doc) return route.continue()
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ message: doc }),
			})
		},
	)
}

test('disk full in the purge binlogs description is red', async ({ page }) => {
	await mockServerDocs(page)

	await page.goto(`/dashboard/servers/${APP_SERVER}/actions`)

	const description = page.getByText('Use this in case of disk full issues')
	await expect(description).toBeVisible({ timeout: 30000 })

	const diskFull = description.locator('span', { hasText: 'disk full' })
	await expect(diskFull).toHaveText('disk full')

	const color = await diskFull.evaluate((el) => getComputedStyle(el).color)
	const rest = await description.evaluate((el) => getComputedStyle(el).color)
	expect(color, 'disk full is not the same grey as the rest').not.toBe(rest)

	const [red, green, blue] = color.match(/\d+/g)!.map(Number)
	expect(red, 'disk full is red').toBeGreaterThan(150)
	expect(green).toBeLessThan(100)
	expect(blue).toBeLessThan(100)
})

test('a description without markup renders as written', async ({ page }) => {
	await mockServerDocs(page)
	await page.goto(`/dashboard/servers/${APP_SERVER}/actions`)

	// The rest of the tab still reads as plain text, entities included.
	await expect(page.getByText('Reboot the server')).toBeVisible({
		timeout: 30000,
	})
	await expect(
		page.getByText('Manage On-Prem Replication & Failover'),
	).toBeVisible()
})
