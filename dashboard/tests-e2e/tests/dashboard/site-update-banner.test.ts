import type { Route } from '@playwright/test'
import { expect, test } from './coverage.fixture'

const SITE_NAME = 'test-updates.fc.frappe.dev'
const CANCELLED_UPDATE_NAME = 'su-cancelled-001'
const BANNER_MESSAGE =
	'Scheduled Site Update for site test-updates.fc.frappe.dev was cancelled: Apps are missing in the destination bench: frappe'

const siteMock = {
	message: {
		name: SITE_NAME,
		status: 'Active',
		// current_plan null prevents the upsell banner from appearing
		current_plan: null,
		group_public: 0,
	},
}

const cancelledUpdatesMock = {
	message: [
		{
			name: CANCELLED_UPDATE_NAME,
			status: 'Cancelled',
			deploy_type: 'Deploy',
			owner: 'test@example.com',
			scheduled_time: '2024-01-01 10:00:00',
			updated_on: null,
			difference: null,
			update_job: null,
			backup_type: null,
			recover_job: null,
		},
	],
}

const notificationMock = {
	message: [
		{
			name: 'notification-001',
			// HTML is rendered via v-html in AlertBanner
			message: `Scheduled Site Update for site <b>${SITE_NAME}</b> was cancelled: Apps are missing in the destination bench: frappe`,
		},
	],
}

const successfulUpdatesMock = {
	message: [
		{
			name: 'su-success-001',
			status: 'Success',
			deploy_type: 'Deploy',
			owner: 'test@example.com',
			scheduled_time: '2024-01-01 12:00:00',
			updated_on: '2024-01-01 12:05:00',
			difference: null,
			update_job: 'job-001',
			backup_type: 'Logical',
			recover_job: null,
		},
		{
			name: CANCELLED_UPDATE_NAME,
			status: 'Cancelled',
			deploy_type: 'Deploy',
			owner: 'test@example.com',
			scheduled_time: '2024-01-01 10:00:00',
			updated_on: null,
			difference: null,
			update_job: null,
			backup_type: null,
			recover_job: null,
		},
	],
}

const emptyListMock = { message: [] }

function doctype(route: Route): string | null {
	return route.request().postDataJSON()?.doctype ?? null
}

async function mockSite(page: Parameters<typeof test>[1]['page']) {
	await page.route('*/**/api/method/press.api.client.get', async (route) => {
		await route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(siteMock),
		})
	})
}

test('shows cancellation notification banner when latest site update is cancelled', async ({
	page,
}) => {
	await mockSite(page)

	await page.route(
		'*/**/api/method/press.api.client.get_list',
		async (route) => {
			if (doctype(route) === 'Site Update') {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify(cancelledUpdatesMock),
				})
			} else if (doctype(route) === 'Press Notification') {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify(notificationMock),
				})
			} else {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify(emptyListMock),
				})
			}
		},
	)

	await page.goto(`/dashboard/sites/${SITE_NAME}/updates`)

	await expect(page.getByText(BANNER_MESSAGE)).toBeVisible()
})

test('hides cancellation banner when latest site update succeeds', async ({
	page,
}) => {
	await mockSite(page)

	await page.route(
		'*/**/api/method/press.api.client.get_list',
		async (route) => {
			if (doctype(route) === 'Site Update') {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify(successfulUpdatesMock),
				})
			} else {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify(emptyListMock),
				})
			}
		},
	)

	await page.goto(`/dashboard/sites/${SITE_NAME}/updates`)

	// Wait for the updates list to be visible before asserting banner absence
	await expect(page.getByText('su-success-001')).toBeVisible()
	await expect(page.getByText(BANNER_MESSAGE)).not.toBeVisible()
})
