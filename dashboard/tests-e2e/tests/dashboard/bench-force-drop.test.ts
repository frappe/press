import type { Page, Request } from '@playwright/test'
import { expect, test } from './coverage.fixture'

const GROUP_NAME = 'bench-9999'
const BENCH_NAME = 'bench-9999-f1-mumbai'

const groupMock = {
	message: {
		name: GROUP_NAME,
		title: 'Test Bench',
		status: 'Active',
		version: 'Version 15',
		public: 0,
		server_team: null,
		are_builds_suspended: 0,
		enable_inplace_updates: 0,
		inplace_update_failed_benches: [],
		actions_access: {},
		eol_versions: [],
		deploy_information: {
			update_available: false,
			deploy_in_progress: false,
			last_deploy: { name: 'deploy-0001' },
			can_run_patch_build: false,
			apps: [],
			removed_apps: [],
			sites: [],
		},
	},
}

const benchListMock = {
	message: [
		{
			name: BENCH_NAME,
			status: 'Broken',
			cluster_image: null,
			cluster_title: 'Mumbai, India',
		},
	],
}

// What ready_to_archive throws when the last archive job failed less than a day ago
const RECENT_FAILURE_MESSAGE =
	'A previous archive job executed in the last 24 hours has failed.' +
	' Please wait for some time before you attempt to archive the bench once again.'

// The boot script assigns window.is_system_user, so a plain init script loses the
// race. An accessor with a setter that drops the write survives it.
async function pinSystemUser(page: Page, isSystemUser: boolean) {
	await page.addInitScript((value) => {
		Object.defineProperty(window, 'is_system_user', {
			configurable: true,
			get: () => value,
			set: () => {},
		})
	}, isSystemUser)
}

async function mockGroupWithOneBench(page: Page) {
	await page.route(
		/\/api\/method\/press\.api\.client\.get\b/,
		async (route) => {
			const url = new URL(route.request().url())
			if (url.searchParams.get('doctype') !== 'Release Group') {
				return route.continue()
			}
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(groupMock),
			})
		},
	)

	await page.route(
		/\/api\/method\/press\.api\.client\.get_list/,
		async (route) => {
			const doctype = route.request().postDataJSON()?.doctype
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(
					doctype === 'Bench' ? benchListMock : { message: [] },
				),
			})
		},
	)
}

function rejectArchiveWithRecentFailure(page: Page) {
	return page.route(
		/\/api\/method\/press\.api\.client\.run_doc_method/,
		async (route) => {
			await route.fulfill({
				status: 417,
				contentType: 'application/json',
				body: JSON.stringify({
					exc_type: 'ArchiveBenchError',
					_server_messages: JSON.stringify([
						JSON.stringify({ message: RECENT_FAILURE_MESSAGE }),
					]),
				}),
			})
		},
	)
}

function acceptArchive(page: Page) {
	return page.route(
		/\/api\/method\/press\.api\.client\.run_doc_method/,
		async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ message: null, docs: [] }),
			})
		},
	)
}

async function openDropBenchDialog(page: Page) {
	await page.goto(`/dashboard/groups/${GROUP_NAME}/sites`)
	await page.getByRole('button', { name: 'Options' }).first().click()
	await page.getByText('Drop Bench').click()
	return page.getByRole('dialog')
}

test('a team user drops a bench with the checks in place', async ({ page }) => {
	await pinSystemUser(page, false)
	await mockGroupWithOneBench(page)
	const dialog = await openDropBenchDialog(page)

	await expect(
		dialog.getByText('Are you sure you want to drop the bench'),
	).toBeVisible()
	await expect(
		dialog.getByText('are skipped for system users'),
	).not.toBeVisible()

	const archiveRequest: Promise<Request> = page.waitForRequest(
		/\/api\/method\/press\.api\.client\.run_doc_method/,
	)
	await rejectArchiveWithRecentFailure(page)
	await dialog.getByRole('button', { name: 'Drop' }).click()

	const body = (await archiveRequest).postDataJSON()
	expect(body.method).toBe('archive')
	expect(body.args.force).toBe(false)
	await expect(page.getByText(RECENT_FAILURE_MESSAGE)).toBeVisible()
})

test('a system user drops the same bench past the checks', async ({ page }) => {
	await pinSystemUser(page, true)
	await mockGroupWithOneBench(page)
	const dialog = await openDropBenchDialog(page)

	await expect(dialog.getByText('are skipped for system users')).toBeVisible()
	await expect(
		dialog.getByText('Sites still on the bench block the drop.'),
	).toBeVisible()

	const archiveRequest: Promise<Request> = page.waitForRequest(
		/\/api\/method\/press\.api\.client\.run_doc_method/,
	)
	await acceptArchive(page)
	await dialog.getByRole('button', { name: 'Drop' }).click()

	const body = (await archiveRequest).postDataJSON()
	expect(body.method).toBe('archive')
	expect(body.args.force).toBe(true)
	await expect(page.getByText('Bench is scheduled to be dropped')).toBeVisible()
})
