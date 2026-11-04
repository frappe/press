import type { Page, Route } from '@playwright/test'
import { expect, test } from './coverage.fixture'

const SITE_NAME = 'test-stop.fc.frappe.dev'
const ACTION_NAME = 'site-action-001'

const siteMock = {
	name: SITE_NAME,
	status: 'Active',
	current_plan: null,
	group_public: 0,
}

function actionMock(status: string) {
	return {
		name: ACTION_NAME,
		action_type: 'Move Site To Different Server / Bench',
		status,
		site: SITE_NAME,
		owner: 'test@example.com',
		creation: '2024-01-01 10:00:00',
		start: '2024-01-01 10:00:01',
		end: null,
		duration: null,
		arguments_dict: { destination_server: 'f1-mumbai.fc.frappe.dev' },
		errors: [],
		steps: [
			{
				name: 'step-001',
				stage: 'Clone and Create Private Bench',
				title: '',
				status: status === 'Running' ? 'Running' : status,
				output: '',
			},
		],
	}
}

async function fulfill(route: Route, message: unknown) {
	await route.fulfill({
		status: 200,
		contentType: 'application/json',
		body: JSON.stringify({ message }),
	})
}

async function mockMigrationPage(page: Page, status: string) {
	await page.route(
		/\/api\/method\/press\.api\.client\.get\b/,
		async (route) => {
			const doctype = new URL(route.request().url()).searchParams.get('doctype')
			if (doctype === 'Site') return fulfill(route, siteMock)
			if (doctype === 'Site Action') return fulfill(route, actionMock(status))
			return route.continue()
		},
	)

	await page.route(/\/api\/method\/press\.api\.client\.get_list/, (route) =>
		fulfill(route, []),
	)

	await page.goto(`/dashboard/sites/${SITE_NAME}/migrations/${ACTION_NAME}`)
	await expect(
		page.getByRole('heading', {
			name: 'Move Site To Different Server / Bench',
		}),
	).toBeVisible({ timeout: 10000 })
}

function stopButton(page: Page) {
	return page.getByRole('button', { name: 'Stop Migration', exact: true })
}

test('stops a running migration from the migration page', async ({ page }) => {
	await mockMigrationPage(page, 'Running')

	let stopped = false
	await page.route(
		/\/api\/method\/press\.api\.client\.run_doc_method/,
		async (route) => {
			const params = route.request().postDataJSON()
			if (params?.method === 'stop_action' && params?.dn === ACTION_NAME) {
				stopped = true
			}
			await fulfill(route, {})
		},
	)

	await stopButton(page).click()
	await expect(
		page.getByText('the work done so far is discarded'),
	).toBeVisible()
	await page
		.getByRole('dialog')
		.getByRole('button', { name: 'Stop Migration' })
		.click()

	await expect.poll(() => stopped).toBe(true)
	await expect(page.getByText('Site migration stopped')).toBeVisible()
})

test('surfaces the reason a migration past the point of no return cannot be stopped', async ({
	page,
}) => {
	await mockMigrationPage(page, 'Running')

	await page.route(
		/\/api\/method\/press\.api\.client\.run_doc_method/,
		async (route) => {
			await route.fulfill({
				status: 417,
				contentType: 'application/json',
				body: JSON.stringify({
					_server_messages: JSON.stringify([
						JSON.stringify({
							message:
								'The site is already being moved by Site Migration <b>sm-001</b>. Stopping it now would leave the site between two benches. Wait for it to finish.',
							title: 'Message',
						}),
					]),
				}),
			})
		},
	)

	await stopButton(page).click()
	await page
		.getByRole('dialog')
		.getByRole('button', { name: 'Stop Migration' })
		.click()

	await expect(
		page.getByText('The site is already being moved by Site Migration'),
	).toBeVisible()
})

test('does not offer stop for a scheduled migration, which is cancelled instead', async ({
	page,
}) => {
	await mockMigrationPage(page, 'Scheduled')

	await expect(stopButton(page)).toHaveCount(0)
})

test('does not offer stop for a finished migration', async ({ page }) => {
	await mockMigrationPage(page, 'Success')

	await expect(stopButton(page)).toHaveCount(0)
})
