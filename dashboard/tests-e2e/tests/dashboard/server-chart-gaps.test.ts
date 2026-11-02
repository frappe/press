import type { Page } from '@playwright/test'
import { expect, test } from './coverage.fixture'

const APP_SERVER = 'f-test-app.frappe.cloud'
const DATABASE_SERVER = 'm-test-db.frappe.cloud'

const serverDoc = {
	name: APP_SERVER,
	title: 'Test Server',
	status: 'Active',
	is_unified_server: 0,
	database_server: DATABASE_SERVER,
	replication_server: null,
}

/** Same shape prometheus_query() returns: null where Prometheus had no sample. */
function iopsPayload(values: (number | null)[]) {
	const start = new Date('2026-08-19T00:00:00')
	return {
		labels: values.map((_, i) =>
			new Date(start.getTime() + i * 600_000)
				.toISOString()
				.slice(0, 19)
				.replace('T', ' '),
		),
		datasets: [{ name: 'nvme0n1 read', values }],
	}
}

async function openIopsChart(page: Page, values: (number | null)[]) {
	await page.setViewportSize({ width: 1440, height: 900 })

	await page.route(
		/\/api\/method\/press\.api\.client\.get\b/,
		async (route) => {
			const url = new URL(route.request().url())
			if (url.searchParams.get('doctype') !== 'Server') return route.continue()
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ message: serverDoc }),
			})
		},
	)

	// Only iops carries data; every other chart on the tab stays empty.
	await page.route(
		/\/api\/method\/press\.api\.server\.analytics/,
		async (route) => {
			const url = new URL(route.request().url())
			const query =
				url.searchParams.get('query') ?? route.request().postDataJSON?.()?.query
			const message =
				query === 'iops' ? iopsPayload(values) : { datasets: [], labels: [] }
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ message }),
			})
		},
	)

	await page.goto(`/dashboard/servers/${APP_SERVER}/analytics`)

	// Empty cards render no .chart, so the only one on the page is Disk I/O.
	const chart = page.locator('.chart').first()
	await chart.scrollIntoViewIfNeeded()
	await expect(chart.locator('svg text').first()).toBeVisible({
		timeout: 30000,
	})
	return chart
}

/** The `d` of the series line: the only stroked path long enough to be a curve. */
async function seriesPath(chart: ReturnType<Page['locator']>) {
	const paths = await chart
		.locator('svg path[fill="none"]')
		.evaluateAll((nodes) => nodes.map((n) => n.getAttribute('d') ?? ''))
	return paths.sort((a, b) => b.length - a.length)[0]
}

test('a run of missing samples breaks the line instead of bridging it', async ({
	page,
}) => {
	// Two hours of data, a two hour hole, two hours of data.
	const values: (number | null)[] = [
		...Array(12).fill(40),
		...Array(12).fill(null),
		...Array(12).fill(40),
	]

	const chart = await openIopsChart(page, values)
	const d = await seriesPath(chart)

	// A bridged line is one continuous subpath; a gap starts a second one.
	const subpaths = d.match(/M/g)?.length ?? 0
	expect(subpaths, 'line is drawn as two separate segments').toBe(2)
})
