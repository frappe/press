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

/** Two disks, read and write each: four series on a chart themed for two. */
function iopsPayload() {
	const start = new Date('2026-08-19T00:00:00')
	const labels = Array.from({ length: 36 }, (_, i) =>
		new Date(start.getTime() + i * 600_000)
			.toISOString()
			.slice(0, 19)
			.replace('T', ' '),
	)
	const series = (name: string, base: number) => ({
		name,
		values: labels.map((_, i) => base + (i % 5)),
	})
	return {
		labels,
		datasets: [
			series('nvme0n1 read', 10),
			series('nvme0n1 write', 20),
			series('nvme1n1 read', 30),
			series('nvme1n1 write', 40),
		],
	}
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
		.toBeGreaterThanOrEqual(4)

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
	expect(errors, 'no uncaught errors while hovering').toEqual([])
	expect(pointerLines, 'axis pointer removed after leave').toBe(0)
})
