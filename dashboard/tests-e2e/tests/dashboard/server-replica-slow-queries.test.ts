import type { Page, Request } from '@playwright/test'
import { expect, test } from './coverage.fixture'

const APP_SERVER = 'f-test-app.frappe.cloud'
const DATABASE_SERVER = 'm-test-db.frappe.cloud'
const REPLICA_SERVER = 'm-test-replica.frappe.cloud'

const serverDoc = {
	name: APP_SERVER,
	title: 'Test Server',
	status: 'Active',
	is_unified_server: 0,
	database_server: DATABASE_SERVER,
	replication_server: REPLICA_SERVER,
}

const LABELS = Array.from({ length: 12 }, (_, i) =>
	new Date(Date.UTC(2026, 7, 19, i))
		.toISOString()
		.slice(0, 19)
		.replace('T', ' '),
)

/** Shape returned by SlowLogGroupByChart.run() */
function slowLogChart(paths: string[]) {
	return {
		labels: LABELS,
		allow_drill_down: false,
		datasets: paths.map((path, series) => ({
			path,
			stack: 'path',
			values: LABELS.map((_, i) => 1 + ((i + series) % 5)),
		})),
	}
}

/** frappe-ui sends resource params in the query string or the POST body. */
function param(request: Request, key: string): string | null {
	const fromUrl = new URL(request.url()).searchParams.get(key)
	if (fromUrl !== null) return fromUrl
	try {
		return String(JSON.parse(request.postData() ?? '{}')[key] ?? '')
	} catch {
		return null
	}
}

async function fulfill(
	route: import('@playwright/test').Route,
	message: unknown,
) {
	await route.fulfill({
		status: 200,
		contentType: 'application/json',
		body: JSON.stringify({ message }),
	})
}

async function mockServerPage(page: Page, doc = serverDoc) {
	await page.setViewportSize({ width: 1440, height: 900 })

	await page.route(
		/\/api\/method\/press\.api\.client\.get\b/,
		async (route) => {
			const url = new URL(route.request().url())
			if (url.searchParams.get('doctype') !== 'Server') return route.continue()
			await fulfill(route, doc)
		},
	)
	await page.route(/\/api\/method\/press\.api\.server\.analytics/, (route) =>
		fulfill(route, { datasets: [], labels: [] }),
	)
	await page.route(
		/\/api\/method\/press\.api\.server\.get_slow_logs_by_site/,
		(route) =>
			fulfill(
				route,
				slowLogChart(['site-a.frappe.cloud', 'site-b.frappe.cloud']),
			),
	)
	await page.route(
		/\/api\/method\/press\.api\.server\.get_slow_logs_by_query/,
		(route) =>
			fulfill(
				route,
				slowLogChart([
					'select * from `tabSales Invoice` where name = ?',
					'select count(*) from `tabGL Entry`',
				]),
			),
	)
}

/** The `name` param of every request to the endpoint, in order. */
function slowLogRequests(page: Page, endpoint: string) {
	const names: string[] = []
	page.on('request', (request) => {
		if (!request.url().includes(endpoint)) return
		names.push(param(request, 'name') ?? '')
	})
	return names
}

test('the replica shows the advanced database charts', async ({ page }) => {
	test.slow()
	await mockServerPage(page)
	const requested = slowLogRequests(page, 'get_slow_logs_by_site')

	await page.goto(
		`/dashboard/servers/${APP_SERVER}/analytics?server=${REPLICA_SERVER}`,
	)

	// The cards were guarded by the "Database Server" label alone, so the
	// replica fetched the data and drew nothing.
	await expect(page.locator('#frequent-slow-queries')).toBeVisible({
		timeout: 30000,
	})
	// Advanced Analytics is below the fold, and toBeVisible does not scroll
	await page.locator('#frequent-slow-queries').scrollIntoViewIfNeeded()
	await expect(page.locator('#slowest-queries')).toBeVisible()
	await expect(page.locator('#queries')).toBeVisible()

	await expect.poll(() => requested.length).toBeGreaterThanOrEqual(2)
	expect(requested.every((name) => name === REPLICA_SERVER)).toBe(true)
})

test('the replica of a unified server shows the database charts', async ({
	page,
}) => {
	test.slow()
	// isServerType maps every type to Unified Server here, so a label check
	// on the chosen option is what finds the replica
	await mockServerPage(page, {
		...serverDoc,
		is_unified_server: 1,
		database_server: null,
	})

	await page.goto(
		`/dashboard/servers/${APP_SERVER}/analytics?server=${REPLICA_SERVER}`,
	)

	await expect(page.locator('#frequent-slow-queries')).toBeVisible({
		timeout: 30000,
	})
})

test('the per-query charts show the queries of the chosen host', async ({
	page,
}) => {
	test.slow()
	await mockServerPage(page)
	const requested = slowLogRequests(page, 'get_slow_logs_by_query')

	await page.goto(
		`/dashboard/servers/${APP_SERVER}/analytics?server=${DATABASE_SERVER}`,
	)

	const byQuery = page.locator('#frequent-slow-queries-by-query')
	await expect(byQuery).toBeVisible({ timeout: 30000 })
	await byQuery.scrollIntoViewIfNeeded()
	await expect(page.locator('#slowest-queries-by-query')).toBeVisible()

	// Query text, not a site name, is the legend of the per-query chart
	await expect(byQuery.getByText('tabGL Entry', { exact: false })).toBeVisible({
		timeout: 15000,
	})

	await expect.poll(() => requested.length).toBeGreaterThanOrEqual(2)
	expect(requested.every((name) => name === DATABASE_SERVER)).toBe(true)

	// Switching to the replica asks for the replica's own slow log. The
	// Server control is a reka-ui select, not a <select>.
	await page.getByRole('combobox').first().click()
	await page.getByRole('option', { name: 'Replication Server' }).click()
	await expect
		.poll(() => requested.filter((name) => name === REPLICA_SERVER).length)
		.toBeGreaterThanOrEqual(2)
})
