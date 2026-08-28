import type { Page, Route } from '@playwright/test'
import { expect, test } from './coverage.fixture'

const SITE_NAME = 'test-cancel.fc.frappe.dev'
const JOB_NAME = 'job-restore-001'

const siteMock = {
	name: SITE_NAME,
	status: 'Active',
	current_plan: null,
	group_public: 0,
}

function jobMock(jobType: string, status: string) {
	return {
		name: JOB_NAME,
		job_type: jobType,
		status,
		site: SITE_NAME,
		owner: 'test@example.com',
		creation: '2024-01-01 10:00:00',
		start: '2024-01-01 10:00:01',
		end: null,
		duration: null,
		steps: [
			{
				name: 'step-001',
				step_name: 'Restore Site',
				status,
				duration: null,
				output: '',
			},
		],
	}
}

async function mockJobPage(
	page: Page,
	jobType: string,
	status: string,
	skippedBackups = false,
) {
	await page.route(
		/\/api\/method\/press\.api\.client\.get\b/,
		async (route) => {
			const doctype = new URL(route.request().url()).searchParams.get('doctype')
			if (doctype === 'Site') return fulfill(route, siteMock)
			if (doctype === 'Agent Job')
				return fulfill(route, jobMock(jobType, status))
			return route.continue()
		},
	)

	await page.route(
		/\/api\/method\/press\.api\.client\.get_list/,
		async (route) => {
			if (route.request().postDataJSON()?.doctype === 'Site Update')
				return fulfill(route, [{ skipped_backups: skippedBackups ? 1 : 0 }])
			return fulfill(route, [])
		},
	)

	await page.goto(`/dashboard/sites/${SITE_NAME}/insights/jobs/${JOB_NAME}`)
	await expect(page.getByRole('heading', { name: jobType })).toBeVisible({
		timeout: 10000,
	})
}

async function fulfill(route: Route, message: unknown) {
	await route.fulfill({
		status: 200,
		contentType: 'application/json',
		body: JSON.stringify({ message }),
	})
}

function cancelButton(page: Page) {
	return page.getByRole('button', { name: 'Cancel Job', exact: true })
}

test('cancels a running restore job from the job page', async ({ page }) => {
	await mockJobPage(page, 'Restore Site', 'Running')

	let cancelled = false
	await page.route(
		/\/api\/method\/press\.api\.client\.run_doc_method/,
		async (route) => {
			const body = route.request().postDataJSON()
			if (body?.dt === 'Agent Job' && body?.method === 'cancel_job') {
				cancelled = true
			}
			await fulfill(route, {})
		},
	)

	await cancelButton(page).click()
	await page
		.getByRole('dialog')
		.getByRole('button', { name: 'Cancel Job' })
		.click()

	await expect.poll(() => cancelled).toBe(true)
})

test('warns about the recovery job when cancelling a site update', async ({
	page,
}) => {
	await mockJobPage(page, 'Update Site Migrate', 'Running')

	await cancelButton(page).click()

	await expect(
		page.getByText(
			'a recovery job will restore the backup and roll the site back',
		),
	).toBeVisible()
})

test('does not offer cancel for a site update that skipped backups', async ({
	page,
}) => {
	await mockJobPage(page, 'Update Site Migrate', 'Running', true)

	await expect(cancelButton(page)).toHaveCount(0)
})

test('does not offer cancel for a finished restore job', async ({ page }) => {
	await mockJobPage(page, 'Restore Site', 'Success')

	await expect(cancelButton(page)).toHaveCount(0)
})

test('does not offer cancel for job types that are not cancellable', async ({
	page,
}) => {
	await mockJobPage(page, 'Migrate Site', 'Running')

	await expect(cancelButton(page)).toHaveCount(0)
})
