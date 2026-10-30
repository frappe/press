import type { Page } from '@playwright/test'
import { expect, test } from './coverage.fixture'

const APP_SERVER = 'f-test-app.frappe.cloud'
const DATABASE_SERVER = 'm-test-db.frappe.cloud'
const SHARED_PLAN_TYPE = 'shared-plan-type-hash'

// The overview renders only once both the app and the database server load.
const plan = {
	name: 'Shared 2GB',
	plan_title: 'Shared 2GB',
	plan_type: SHARED_PLAN_TYPE,
	vcpu: 1,
	memory: 2048,
	disk: 25,
	price_inr: 500,
	price_usd: 10,
}

const serverFields = {
	status: 'Active',
	is_unified_server: 0,
	replication_server: null,
	current_plan: plan,
	usage: { vcpu: 0.1, memory: 512, disk: 5 },
	disk_size: 25,
	storage_plan: { price_inr: 10, price_usd: 0.2 },
	actions: [],
}

const appServerDoc = {
	...serverFields,
	name: APP_SERVER,
	title: 'Test Server',
	database_server: DATABASE_SERVER,
}

const databaseServerDoc = {
	...serverFields,
	name: DATABASE_SERVER,
	title: 'Test Database Server',
}

// The team doc is the real one with is_desk_user forced off, so the
// test runs as a plain user.
async function mockDocs(page: Page) {
	await page.route(
		/\/api\/method\/press\.api\.client\.get\b/,
		async (route) => {
			const doctype = new URL(route.request().url()).searchParams.get('doctype')
			const doc =
				doctype === 'Server'
					? appServerDoc
					: doctype === 'Database Server'
						? databaseServerDoc
						: null
			if (doc) {
				return route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ message: doc }),
				})
			}
			if (doctype === 'Team') {
				const response = await route.fetch()
				const json = await response.json()
				json.message.is_desk_user = 0
				return route.fulfill({ response, json })
			}
			return route.continue()
		},
	)
	await page.route(/\/api\/method\/press\.api\.server\.plans/, (route) =>
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({
				message: {
					plans: [],
					types: { [SHARED_PLAN_TYPE]: { title: 'Shared Instance' } },
				},
			}),
		}),
	)
}

test('a plain user sees the shared badge on the server overview', async ({
	page,
}) => {
	await mockDocs(page)
	await page.goto(`/dashboard/servers/${APP_SERVER}/overview`)

	// One badge for the app server plan, one for the database server plan.
	const badges = page.getByText('Shared', { exact: true })
	await expect(badges).toHaveCount(2, { timeout: 30000 })
	await expect(badges.first()).toBeVisible()
})
