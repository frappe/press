import { expect, test } from './coverage.fixture'

const GROUP_NAME = 'bench-9999'
const PIPELINE_NAME = 'pipeline-0001'
const BUILD_NAME = 'build-0001'
const DOC_URL =
	'https://docs.frappe.io/cloud/private-benches/common-issues/frappe-listed-as-a-python-dependency'

const groupMock = {
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
		update_available: false,
		deploy_in_progress: false,
		last_deploy: { name: PIPELINE_NAME },
		can_run_patch_build: false,
		apps: [],
		removed_apps: [],
		sites: [],
	},
}

const pipelineMock = {
	doctype: 'Release Pipeline',
	name: PIPELINE_NAME,
	status: 'Failure',
	owner: 'developer@example.com',
	steps: {
		doctype: 'Release Pipeline',
		name: PIPELINE_NAME,
		status: 'Failure',
		start: '2026-09-10T07:15:00',
		end: '2026-09-10T07:19:01',
		duration: 241,
		stages: [
			{ name: 'checks', label: 'Pre-release checks', status: 'Success' },
			{ name: 'prepare', label: 'Preparing deployment', status: 'Success' },
			{
				name: 'build',
				label: 'Building',
				status: 'Failure',
				builds: [
					{
						doctype: 'Deploy Candidate Build',
						name: BUILD_NAME,
						status: 'Failure',
						architecture: 'x86_64',
					},
				],
			},
		],
	},
}

const buildMock = {
	doctype: 'Deploy Candidate Build',
	name: BUILD_NAME,
	status: 'Failure',
	group: GROUP_NAME,
	build_steps: [
		{
			name: 'step-1',
			stage: 'Install Apps',
			step: 'Frappe Framework',
			status: 'Success',
			duration: 30,
			output: '',
		},
		{
			name: 'step-2',
			stage: 'Install Apps',
			step: 'my_app',
			status: 'Failure',
			duration: 0,
			output:
				'hint: `frappe` (v15.120.1) was included because `my_app` (v0.0.1) depends on `frappe`',
		},
	],
}

// Produced by get_details() in press/press/doctype/deploy_candidate/deploy_notifications.py
// for a uv resolution failure where the app lists frappe under [project] dependencies.
const notificationMock = {
	name: 'notif-0001',
	title: 'my_app lists frappe as a Python dependency',
	message:
		'<p><b>my_app</b> declares <code>frappe</code> under <code>[project] dependencies</code>' +
		' in its <b>pyproject.toml</b>.</p> <p>Please <b>remove</b> <code>frappe</code> from the' +
		' dependencies list of your app and deploy again. To declare which Frappe versions your' +
		' app supports, use the <code>[tool.bench.frappe-dependencies]</code> section' +
		' instead.</p>',
	document_name: BUILD_NAME,
	class: 'Error',
	assistance_url: DOC_URL,
}

// Produced by get_details() for a build failure it does not recognise.
const genericNotificationMock = {
	name: 'notif-0002',
	title: 'Build Failed',
	message: 'Image build failed at step <b>Install Apps - my_app</b>.',
	document_name: BUILD_NAME,
	class: 'Error',
	assistance_url: null,
}

async function openFailedBuild(page, notification) {
	await page.route(
		/\/api\/method\/press\.api\.client\.get\b/,
		async (route) => {
			const url = new URL(route.request().url())
			const docs = {
				'Release Group': groupMock,
				'Release Pipeline': pipelineMock,
				'Deploy Candidate Build': buildMock,
			}
			const doc = docs[url.searchParams.get('doctype')]
			if (!doc) return route.continue()

			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ message: doc }),
			})
		},
	)

	await page.route(
		/\/api\/method\/press\.api\.client\.get_list/,
		async (route) => {
			const request = route.request()
			const payload = decodeURIComponent(
				request.url() + (request.postData() || ''),
			)
			// The panel fetches errors and warnings separately, this build only errored.
			const wantsErrors =
				payload.includes('Press Notification') && payload.includes('Error')
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ message: wantsErrors ? [notification] : [] }),
			})
		},
	)

	await page.goto(`/dashboard/groups/${GROUP_NAME}/pipeline/${PIPELINE_NAME}`)
	await expect(page.getByRole('tab', { name: 'Issues' })).toBeVisible()
}

// Optional capture for docs/PR screenshots
async function capture(page, envVariable) {
	if (!process.env[envVariable]) return
	await page.locator('main').screenshot({ path: process.env[envVariable] })
}

test('names the app that lists frappe as a dependency on a failed build', async ({
	page,
}) => {
	await openFailedBuild(page, notificationMock)

	await expect(
		page.getByText('my_app lists frappe as a Python dependency'),
	).toBeVisible()
	await expect(
		page.getByText(
			'Please remove frappe from the dependencies list of your app and deploy again',
		),
	).toBeVisible()
	await expect(page.getByRole('link', { name: 'Go to docs' })).toHaveAttribute(
		'href',
		DOC_URL,
	)

	await capture(page, 'PLAYWRIGHT_ISSUE_SHOT_AFTER')
})

test('keeps the generic build failure notification when the cause is unknown', async ({
	page,
}) => {
	await openFailedBuild(page, genericNotificationMock)

	await expect(
		page.getByText('Image build failed at step Install Apps - my_app'),
	).toBeVisible()
	await expect(page.getByRole('link', { name: 'Go to docs' })).toHaveCount(0)

	await capture(page, 'PLAYWRIGHT_ISSUE_SHOT_BEFORE')
})
