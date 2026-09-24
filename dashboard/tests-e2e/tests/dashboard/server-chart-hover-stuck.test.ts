import { expect, test } from './coverage.fixture'

const APP_SERVER = 'f-test-app.frappe.cloud'

const serverDoc = {
	name: APP_SERVER,
	title: 'Test Server',
	status: 'Active',
	is_unified_server: 0,
	database_server: 'm-test-db.frappe.cloud',
	replication_server: null,
}

/** Three disks, read and write each: six series, more than the four colours. */
const DISKS = ['nvme0n1', 'nvme1n1', 'nvme2n1']

function iopsPayload() {
	const start = new Date('2026-08-19T00:00:00')
	const labels = Array.from({ length: 36 }, (_, i) =>
		new Date(start.getTime() + i * 600_000)
			.toISOString()
			.slice(0, 19)
			.replace('T', ' '),
	)
	const datasets = DISKS.flatMap((disk, d) =>
		['read', 'write'].map((operation, o) => ({
			name: `${disk} ${operation}`,
			values: labels.map((_, i) => 10 * (2 * d + o + 1) + (i % 5)),
		})),
	)
	return { labels, datasets }
}

test('hovering a chart with more series than theme colours keeps rendering', async ({
	page,
}) => {
	const errors: string[] = []
	page.on('pageerror', (e) => errors.push(e.message))
	await page.setViewportSize({ width: 1440, height: 900 })

	await page.route(
		/\/api\/method\/press\.api\.client\.get\b/,
		async (route) => {
			const url = new URL(route.request().url())
			if (url.searchParams.get('doctype') !== 'Server') return route.continue()
			await route.fulfill({ json: { message: serverDoc } })
		},
	)
	await page.route(
		/\/api\/method\/press\.api\.server\.analytics/,
		async (route) => {
			const query = route.request().postDataJSON?.()?.query
			const message =
				query === 'iops' ? iopsPayload() : { datasets: [], labels: [] }
			await route.fulfill({ json: { message } })
		},
	)

	await page.goto(`/dashboard/servers/${APP_SERVER}/analytics`)
	const chart = page.locator('#disk-i-o .chart svg')
	await chart.scrollIntoViewIfNeeded()
	await expect
		.poll(() => chart.locator('path[fill="none"][stroke]').count(), {
			timeout: 30000,
		})
		.toBeGreaterThanOrEqual(DISKS.length * 2)

	const box = (await chart.boundingBox())!
	const y = box.y + box.height / 2
	for (let x = box.x + 60; x < box.x + box.width - 30; x += 8) {
		await page.mouse.move(x, y)
		await page.waitForTimeout(20)
	}
	await page.mouse.move(box.x + box.width / 2, box.y + box.height + 200)
	await page.waitForTimeout(500)

	const pointerLines = await chart
		.locator('line[stroke-dasharray], path[stroke-dasharray]')
		.count()
	// The page also calls endpoints this test does not mock. Their errors are
	// not the chart's, so they must not fail this test.
	const chartErrors = errors.filter((e) => !e.includes('/api/method/'))
	expect(chartErrors, 'no render errors while hovering').toEqual([])
	expect(pointerLines, 'axis pointer removed after leave').toBe(0)
})
