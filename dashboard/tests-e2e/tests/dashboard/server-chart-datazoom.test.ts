import type { Locator, Page } from '@playwright/test'
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

const RANGE_START = new Date('2026-08-19T00:00:00')
const BUCKETS = 24
const BUCKET_MS = 3600_000

/** prometheus_query() labels are local wall clock time, not UTC. */
function label(milliseconds: number) {
	const date = new Date(milliseconds)
	const pad = (value: number) => String(value).padStart(2, '0')
	return (
		`${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
		` ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
	)
}

const LABELS = Array.from({ length: BUCKETS }, (_, i) =>
	label(RANGE_START.getTime() + i * BUCKET_MS),
)

/** Same shape prometheus_query() returns: one dataset, one label per bucket. */
const cpuPayload = {
	labels: LABELS,
	datasets: [
		{ name: 'user', values: LABELS.map((_, i) => 10 + ((i * 7) % 60)) },
	],
}

type Request = { query: string; start: Date; end: Date }

/** Loads the analytics tab with CPU as the only chart that has data. */
async function openCpuChart(page: Page, requests: Request[]) {
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

	await page.route(
		/\/api\/method\/press\.api\.server\.analytics/,
		async (route) => {
			const url = new URL(route.request().url())
			const body = route.request().postDataJSON?.() ?? {}
			const param = (key: string) => url.searchParams.get(key) ?? body[key]
			const query = param('query')
			requests.push({
				query,
				start: new Date(param('start')),
				end: new Date(param('end')),
			})
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					message: query === 'cpu' ? cpuPayload : { datasets: [], labels: [] },
				}),
			})
		},
	)

	await page.goto(`/dashboard/servers/${APP_SERVER}/analytics`)

	const chart = page.locator('.chart').first()
	await expect(chart.locator('svg text').first()).toBeVisible({
		timeout: 30000,
	})
	return chart
}

/** Drags across the plot area, from one fraction of its width to another. */
async function dragAcrossPlot(
	page: Page,
	chart: Locator,
	from: number,
	to: number,
) {
	const box = (await chart.boundingBox())!
	// Plot area sits inside the LineChart grid: 50px left, 20px right.
	const plotStart = box.x + 50
	const plotWidth = box.width - 70
	const y = box.y + box.height / 2

	// The chart arms drag-to-zoom on its first finished render.
	await page.waitForTimeout(2000)
	await page.mouse.move(plotStart + plotWidth * from, y)
	await page.mouse.down()
	await page.mouse.move(plotStart + plotWidth * to, y, { steps: 10 })
	await page.mouse.up()
}

test('dragging over a server line chart narrows the range to the selection', async ({
	page,
}) => {
	const requests: Request[] = []
	const chart = await openCpuChart(page, requests)
	requests.length = 0

	await dragAcrossPlot(page, chart, 0.25, 0.75)

	// The zoom switches the duration to custom, which shows the two pickers.
	await expect(page.getByText('Start')).toBeVisible({ timeout: 10000 })
	await expect(page.getByText('End')).toBeVisible()

	await expect
		.poll(() => requests.some((request) => request.query === 'cpu'), {
			timeout: 10000,
		})
		.toBe(true)

	// One refetch, not two: the range must never pass through a default window
	// on its way to the dragged one, or every chart on the tab reloads twice.
	const cpuRequests = requests.filter((request) => request.query === 'cpu')
	expect(cpuRequests).toHaveLength(1)

	// The refetch asks for the dragged window, not the 1 hour default.
	const zoomed = cpuRequests.pop()!
	const dataStart = RANGE_START.getTime()
	const span = (BUCKETS - 1) * BUCKET_MS
	const tolerance = 2 * BUCKET_MS

	expect(
		Math.abs(zoomed.start.getTime() - (dataStart + span * 0.25)),
	).toBeLessThan(tolerance)
	expect(
		Math.abs(zoomed.end.getTime() - (dataStart + span * 0.75)),
	).toBeLessThan(tolerance)
})
