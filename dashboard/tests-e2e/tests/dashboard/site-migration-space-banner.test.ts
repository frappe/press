import type { Route } from '@playwright/test'
import { expect, test } from './coverage.fixture'

const SITE_NAME = 'test-migrate.fc.frappe.dev'
const SERVER_NAME = 'f1-mumbai.fc.frappe.dev'

// Mirrors a real frappe `frappe.throw(..., InsufficientSpaceOnServer)` response.
// frappe-ui parses `_server_messages` into the error's `messages`, which is what
// the banner's `isInsufficientSpaceError` check reads.
const insufficientSpaceError = {
	exc_type: 'InsufficientSpaceOnServer',
	_server_messages: JSON.stringify([
		JSON.stringify({
			message:
				'Insufficient estimated space on Database server to migrate site. Required: 10.00 GB, Available: 2.00 GB (Need 8.00 GB more).',
			title: 'Message',
		}),
	]),
}

const siteMock = {
	message: {
		name: SITE_NAME,
		status: 'Active',
		current_plan: null,
		group_public: 0,
		server: SERVER_NAME,
	},
}

// `run_doc_method` responses include `docs`; frappe-ui returns the whole
// response (not just `.message`) when `docs` is present, and the dialog reads
// `data.message`. Mirror that shape.
const migrationOptionsMock = {
	message: {
		has_recent_failed_migration: true,
		'Move Site To Different Server / Bench': {
			hidden: false,
			allow_scheduling: false,
			button_label: 'Move Site',
			options: {
				available_release_groups: [],
				dedicated_servers_for_new_release_group: [
					{ name: SERVER_NAME, title: 'My Server' },
				],
			},
		},
	},
	docs: [{}],
}

const emptyListMock = { message: [] }

function docMethod(route: Route): string | null {
	return route.request().postDataJSON()?.method ?? null
}

async function mockSite(page: Parameters<typeof test>[1]['page']) {
	await page.route(
		/\/api\/method\/press\.api\.client\.get\b/,
		async (route) => {
			const url = new URL(route.request().url())
			if (url.searchParams.get('doctype') === 'Site') {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify(siteMock),
				})
			} else {
				await route.continue()
			}
		},
	)

	await page.route(
		/\/api\/method\/press\.api\.client\.get_list/,
		async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(emptyListMock),
			})
		},
	)
}

test('shows cleanup-actions banner when a server-move migration retry fails for lack of disk space', async ({
	page,
}) => {
	await mockSite(page)

	await page.route(
		/\/api\/method\/press\.api\.client\.run_doc_method/,
		async (route) => {
			const method = docMethod(route)
			if (method === 'get_migration_options') {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify(migrationOptionsMock),
				})
			} else if (method === 'create_migration_plan') {
				// The retry: destination server still doesn't have enough space.
				await route.fulfill({
					status: 417,
					contentType: 'application/json',
					body: JSON.stringify(insufficientSpaceError),
				})
			} else {
				await route.continue()
			}
		},
	)

	await page.goto(`/dashboard/sites/${SITE_NAME}/migrations`)

	// Open the migrate dialog, move the site to a new bench on a dedicated
	// server, then re-attempt. The comboboxes appear in order as fields unlock.
	const dialog = page.getByRole('dialog', { name: 'Migrate Site' })
	const comboboxes = dialog.getByRole('combobox')
	await page.getByRole('button', { name: 'Trigger Migration' }).click()
	await expect(dialog).toBeVisible()

	await comboboxes.nth(0).click() // migration type
	await page
		.getByRole('option', { name: 'Move Site To Different Server / Bench' })
		.click()
	await dialog.getByPlaceholder('Provide New Bench Name').fill('Test Bench')
	await comboboxes.nth(1).click() // server type
	await page.getByRole('option', { name: 'Dedicated Server' }).click()
	await dialog.getByRole('button', { name: 'Show popup' }).click()
	await page.getByRole('option', { name: /My Server/ }).click()
	await dialog.getByRole('button', { name: 'Move Site' }).click()

	// Banner explains the failed attempt and offers add-storage + the cleanup actions
	await expect(
		dialog.getByText('The previous migration used up some storage'),
	).toBeVisible({ timeout: 10000 })
	await expect(
		dialog.getByRole('link', { name: 'Add more storage' }),
	).toHaveAttribute('href', 'https://docs.frappe.io/cloud/storage-addons')
	await expect(
		dialog.getByRole('link', { name: 'Learn about Cleanup Server' }),
	).toHaveAttribute(
		'href',
		'https://docs.frappe.io/cloud/storage-addons#how-to-force-cleanup-unused-files',
	)
	await expect(
		dialog.getByRole('link', { name: 'Learn about Forcefully Purge Binlogs' }),
	).toHaveAttribute(
		'href',
		'https://docs.frappe.io/cloud/database-server-actions#view-purge-binlogs',
	)

	// Optional capture for docs/PR screenshots
	if (process.env.PLAYWRIGHT_BANNER_SHOT) {
		await dialog.screenshot({ path: process.env.PLAYWRIGHT_BANNER_SHOT })
	}

	// Each button opens the server's Actions tab with an `action` query param, which
	// makes ServerActionCell auto-open that action's dialog.
	const [cleanupTab] = await Promise.all([
		page.waitForEvent('popup'),
		dialog.getByRole('button', { name: 'Cleanup Server' }).click(),
	])
	const cleanupUrl = new URL(cleanupTab.url())
	expect(cleanupUrl.pathname).toContain(`/servers/${SERVER_NAME}/actions`)
	expect(cleanupUrl.searchParams.get('action')).toBe('Cleanup Server')
	await cleanupTab.close()

	const [purgeTab] = await Promise.all([
		page.waitForEvent('popup'),
		dialog.getByRole('button', { name: 'Forcefully Purge Binlogs' }).click(),
	])
	const purgeUrl = new URL(purgeTab.url())
	expect(purgeUrl.pathname).toContain(`/servers/${SERVER_NAME}/actions`)
	expect(purgeUrl.searchParams.get('action')).toBe('Forcefully Purge Binlogs')
	await purgeTab.close()

	// Optional hold so the banner can be eyeballed during a headed demo run
	if (process.env.PLAYWRIGHT_BANNER_PAUSE) {
		await page.waitForTimeout(Number(process.env.PLAYWRIGHT_BANNER_PAUSE))
	}
})
