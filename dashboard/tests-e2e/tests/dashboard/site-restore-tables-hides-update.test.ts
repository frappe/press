import { expect, test } from './coverage.fixture'

const SITE_NAME = 'test-restore.fc.frappe.dev'

// A broken site whose logical-backup migrate update failed, with a newer bench waiting.
const siteMock = {
	message: {
		name: SITE_NAME,
		status: 'Broken',
		current_plan: null,
		group_public: 0,
		// The header needs these for the breadcrumbs and the version notice
		server: 'f1-test',
		server_title: 'Test Server',
		group: 'bench-test',
		group_title: 'Test Bench',
		version: 'Version 15',
		eol_versions: [],
		fatal_site_update: 'su-fatal-001',
		fatal_update: {
			deploy_type: 'Migrate',
			backup_type: 'Logical',
			update_job: 'job-001',
			recover_job: 'job-002',
			update_start: '2024-01-01 10:00:00',
		},
		has_scheduled_updates: false,
		update_information: { update_available: true },
	},
}

test('hides Update Available while Restore Tables is the only way forward', async ({
	page,
}) => {
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
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ message: [] }),
			})
		},
	)

	await page.goto(`/dashboard/sites/${SITE_NAME}`)

	await expect(
		page.getByRole('button', { name: 'Restore Tables' }),
	).toBeVisible()
	await expect(
		page.getByRole('button', { name: 'Update Available' }),
	).not.toBeVisible()
})
