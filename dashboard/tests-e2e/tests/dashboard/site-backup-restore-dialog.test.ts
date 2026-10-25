import { expect, test } from './coverage.fixture'

const SITE_NAME = 'test-backup-restore.fc.frappe.dev'

const siteMock = {
	message: {
		name: SITE_NAME,
		status: 'Active',
		current_plan: null,
		group_public: 0,
		// The header needs these for the breadcrumbs and the version notice
		server: 'f1-test',
		server_title: 'Test Server',
		group: 'bench-test',
		group_title: 'Test Bench',
		version: 'Version 15',
		eol_versions: [],
	},
}

const offsiteBackup = {
	name: 'backup-offsite',
	status: 'Success',
	creation: '2026-10-25 17:01:00',
	offsite: 1,
	physical: 0,
	remote_database_file: 'remote-db',
	remote_public_file: 'remote-public',
	remote_private_file: 'remote-private',
	remote_config_file: 'remote-config',
}

const physicalBackup = {
	name: 'backup-physical',
	status: 'Success',
	creation: '2026-10-24 17:01:00',
	offsite: 0,
	physical: 1,
}

async function mockSiteWithBackups(page: Parameters<typeof test>[1]['page']) {
	await page.route(
		/\/api\/method\/press\.api\.client\.get\b/,
		async (route) => {
			const url = new URL(route.request().url())
			if (url.searchParams.get('doctype') !== 'Site') {
				return route.continue()
			}
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(siteMock),
			})
		},
	)

	await page.route(
		/\/api\/method\/press\.api\.client\.get_list/,
		async (route) => {
			const doctype = route.request().postDataJSON()?.doctype
			const message =
				doctype === 'Site Backup' ? [offsiteBackup, physicalBackup] : []
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ message }),
			})
		},
	)
}

async function openRestoreDialog(
	page: Parameters<typeof test>[1]['page'],
	rowText: string,
	title: string,
) {
	await mockSiteWithBackups(page)
	await page.goto(`/dashboard/sites/${SITE_NAME}/backups`)

	// The list renders each row as a button, with the actions menu button inside
	await page
		.getByRole('button', { name: new RegExp(`Backup on .*${rowText}`) })
		.getByRole('button')
		.click()
	await page
		.getByRole('menuitem', { name: 'Restore Backup', exact: true })
		.click()
	return page.getByRole('dialog', { name: title })
}

test('restoring an offsite backup warns that data and apps are overwritten and confirms with a red button', async ({
	page,
}) => {
	const dialog = await openRestoreDialog(page, 'Oct 25, 2026', 'Restore Backup')

	await expect(dialog).toContainText(
		'This will overwrite all data & apps in your site with those from the backup.',
	)
	// frappe-ui paints a solid button by theme: gray is near-black, red is red
	await expect(dialog.getByRole('button', { name: 'Confirm' })).toHaveClass(
		/bg-surface-red-5/,
	)
})

test('restoring a physical backup warns that data and apps are overwritten and confirms with a red button', async ({
	page,
}) => {
	const dialog = await openRestoreDialog(
		page,
		'Oct 24, 2026',
		'Restore Physical Backup',
	)

	await expect(dialog).toContainText(
		'This will overwrite all data & apps in your site with those from the backup.',
	)
	await expect(dialog.getByRole('button', { name: 'Confirm' })).toHaveClass(
		/bg-surface-red-5/,
	)
})
