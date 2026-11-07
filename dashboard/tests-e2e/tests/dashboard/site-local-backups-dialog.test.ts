import type { Page, Request } from '@playwright/test'
import { expect, test } from './coverage.fixture'

const SITE_NAME = 'local-backups.fc.frappe.dev'
const SITE_DOMAIN = 'erp.example.com'

const siteDoc = {
	name: SITE_NAME,
	host_name: SITE_DOMAIN,
	status: 'Active',
	// current_plan null prevents the upsell banner from appearing
	current_plan: null,
	group_public: 0,
	setup_wizard_complete: 1,
	actions: [
		{
			action: 'Manage local backups',
			description:
				'View, download or delete backups stored on the server in private/backups',
			button_label: 'Manage',
			doc_method: 'dummy',
		},
	],
}

const localBackups = [
	{
		file: '20261012_020000-local-backups_fc_frappe_dev-database.sql.gz',
		type: 'Database',
		size: 52_428_800,
		modified: '2026-10-12T02:00:05+00:00',
	},
	{
		file: '20261012_020000-local-backups_fc_frappe_dev-files.tar',
		type: 'Public Files',
		size: 1_073_741_824,
		modified: '2026-10-12T02:01:10+00:00',
	},
	{
		file: '20261011_020000-local-backups_fc_frappe_dev-database.sql.gz',
		type: 'Database',
		size: 51_380_224,
		modified: '2026-10-11T02:00:04+00:00',
	},
].map((backup) => ({
	...backup,
	download_url: `https://${SITE_DOMAIN}/backups/${backup.file}`,
}))

function respond(message: unknown) {
	// run_doc_method returns the doc alongside, which frappe-ui expects
	return {
		status: 200,
		contentType: 'application/json',
		body: JSON.stringify({ message, docs: [siteDoc] }),
	}
}

async function openLocalBackupsDialog(page: Page) {
	const deleteRequests: Request[] = []

	await page.route(
		/\/api\/method\/press\.api\.client\.get\b/,
		async (route) => {
			const url = new URL(route.request().url())
			if (url.searchParams.get('doctype') !== 'Site') return route.continue()
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ message: siteDoc }),
			})
		},
	)
	await page.route(
		/\/api\/method\/press\.api\.client\.get_list/,
		async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ message: [] }),
			})
		},
	)
	await page.route(
		/\/api\/method\/press\.api\.client\.run_doc_method/,
		async (route) => {
			const body = route.request().postDataJSON()
			if (body.method === 'get_local_backups') {
				return route.fulfill(respond(localBackups))
			}
			if (body.method === 'delete_local_backups') {
				deleteRequests.push(route.request())
				return route.fulfill(respond({ deleted: body.args.files, missing: [] }))
			}
			return route.continue()
		},
	)

	await page.goto(`/dashboard/sites/${SITE_NAME}/actions`)
	await page
		.getByText('Manage local backups')
		.locator('xpath=ancestor::div[contains(@class, "justify-between")][1]')
		.getByRole('button', { name: 'Manage' })
		.click({ timeout: 30000 })

	const dialog = page.getByRole('dialog')
	await expect(dialog.getByText(localBackups[0].file)).toBeVisible()
	return { dialog, deleteRequests }
}

test('local backups dialog lists backups with download links on the primary domain', async ({
	page,
}) => {
	const { dialog } = await openLocalBackupsDialog(page)

	await expect(dialog.getByText('1 GB')).toBeVisible()
	await expect(dialog.getByText('logged in to the site')).toBeVisible()
	await expect(dialog.getByTitle(/^Download/).first()).toHaveAttribute(
		'href',
		`https://${SITE_DOMAIN}/backups/${localBackups[0].file}`,
	)
})

test('local backups dialog deletes only after the loss of data is acknowledged', async ({
	page,
}) => {
	const { dialog, deleteRequests } = await openLocalBackupsDialog(page)

	await dialog.getByText(localBackups[2].file).click()
	await dialog.getByRole('button', { name: 'Delete selected' }).click()

	await expect(dialog.getByText("can't be recovered").first()).toBeVisible()
	const confirm = dialog.getByRole('button', { name: 'Delete 1 backup' })
	await expect(confirm).toBeDisabled()

	await dialog.getByText('I understand these backups').click()
	await confirm.click()

	await expect.poll(() => deleteRequests.length).toBe(1)
	expect(deleteRequests[0].postDataJSON().args.files).toEqual([
		localBackups[2].file,
	])
})

test('local backups dialog sends no delete when the user goes back', async ({
	page,
}) => {
	const { dialog, deleteRequests } = await openLocalBackupsDialog(page)

	await dialog.getByText(localBackups[2].file).click()
	await dialog.getByRole('button', { name: 'Delete selected' }).click()
	await dialog.getByRole('button', { name: 'Back' }).click()

	await expect(dialog.getByText(localBackups[0].file)).toBeVisible()
	expect(deleteRequests).toHaveLength(0)
})
