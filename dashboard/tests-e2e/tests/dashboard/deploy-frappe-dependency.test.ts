import { expect, test } from './coverage.fixture'

const GROUP_NAME = 'test-bench-group'
const DOCS_URL =
	'https://docs.frappe.io/cloud/private-benches/common-issues/frappe-listed-as-a-python-dependency'
// The dialog renders the message as HTML, so the code tags do not show up in the text
const ERROR_MESSAGE =
	'ERPNext lists <code>frappe</code> under <code>[project]</code> <code>dependencies</code> in its pyproject.toml. Remove <code>frappe</code> from <code>dependencies</code> and deploy again. ' +
	`<a href="${DOCS_URL}" target="_blank" class="underline">Why?</a>`
const RENDERED_MESSAGE =
	'ERPNext lists frappe under [project] dependencies in its pyproject.toml. Remove frappe from dependencies and deploy again.'

const groupMock = {
	message: {
		name: GROUP_NAME,
		title: 'Test Bench Group',
		status: 'Active',
		version: 'Version 15',
		public: 0,
		enable_inplace_updates: 0,
		are_builds_suspended: 0,
		deploy_information: {
			// no last_deploy means this is a first deploy: apps are preselected
			// and the dialog opens straight on the deploy button
			last_deploy: null,
			update_available: true,
			deploy_in_progress: false,
			has_running_release_pipeline: false,
			bench_creation_underway: false,
			can_run_patch_build: false,
			number_of_apps: 1,
			removed_apps: [],
			sites: [],
			apps: [
				{
					name: 'erpnext',
					app: 'erpnext',
					title: 'ERPNext',
					source: 'erpnext-source',
					update_available: true,
					next_release: 'release-002',
					next_release_hash: 'b'.repeat(40),
					current_hash: 'a'.repeat(40),
					current_branch: 'version-15',
					repository_url: 'https://github.com/frappe/erpnext',
					will_branch_change: false,
					releases: [
						{
							name: 'release-002',
							hash: 'b'.repeat(40),
							message: 'fix: something',
							is_yanked: false,
							is_mandatory: false,
						},
					],
				},
			],
		},
	},
}

// Frappe returns validation errors as 417 with the message in _server_messages
const validationError = {
	exc_type: 'ValidationError',
	_server_messages: JSON.stringify([
		JSON.stringify({ message: ERROR_MESSAGE }),
	]),
}

test('shows the error when an app lists frappe as a python dependency', async ({
	page,
}) => {
	await page.route(
		/\/api\/method\/press\.api\.client\.get\b/,
		async (route) => {
			const url = new URL(route.request().url())
			if (url.searchParams.get('doctype') === 'Release Group') {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify(groupMock),
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
				body: JSON.stringify(validationError),
			})
		},
	)

	await page.goto(`/dashboard/groups/${GROUP_NAME}/apps`)

	await page.getByRole('button', { name: 'Deploy Now' }).click()
	await expect(page.getByText('Deploy Apps')).toBeVisible()

	await page.getByRole('button', { name: 'Deploy now' }).click()

	const error = page.getByRole('alert').filter({ hasText: RENDERED_MESSAGE })
	await expect(error).toBeVisible({ timeout: 10000 })
	await expect(error.getByRole('link', { name: 'Why?' })).toHaveAttribute(
		'href',
		DOCS_URL,
	)
})
