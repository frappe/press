import { expect, test } from './coverage.fixture'

const GROUP_NAME = 'bench-9999'

// No apps to update, so the dialog opens straight on the deploy step.
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
		deploy_information: {
			update_available: true,
			deploy_in_progress: false,
			last_deploy: { name: 'deploy-0001' },
			can_run_patch_build: false,
			apps: [],
			removed_apps: [],
			sites: [],
		},
	},
}

// The message check_if_app_updated throws when a retry changes nothing.
const BLOCKED_RETRY_MESSAGE =
	'App <b>HR</b> failed in the previous build. The app is still on release' +
	' <b>a1b2c3d4e5</b>. <b>Push a fix to the app, then fetch the new release.</b>' +
	' To build without a change, select <b>"I understand, run deploy anyway"</b>. ' +
	'<a href="https://docs.frappe.io/cloud/common-issues/build-might-fail" target="_blank" class="underline">Learn more</a>'

test('shows how to fix a blocked deploy retry', async ({ page }) => {
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
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ message: [] }),
			})
		},
	)

	await page.route(
		/\/api\/method\/press\.api\.bench\.deploy_and_update/,
		async (route) => {
			await route.fulfill({
				status: 417,
				contentType: 'application/json',
				body: JSON.stringify({
					exc_type: 'BuildValidationError',
					_server_messages: JSON.stringify([
						JSON.stringify({ message: BLOCKED_RETRY_MESSAGE }),
					]),
				}),
			})
		},
	)

	await page.goto(`/dashboard/groups/${GROUP_NAME}`)
	await page.getByRole('button', { name: 'Update Available' }).click()
	await page
		.getByRole('button', { name: /Deploy/ })
		.last()
		.click()

	await expect(page.getByText('Build might fail')).toBeVisible()
	await expect(
		page.getByText('The app is still on release a1b2c3d4e5'),
	).toBeVisible()
	await expect(
		page.getByRole('checkbox', { name: 'I understand, run deploy anyway' }),
	).toBeVisible()
})
