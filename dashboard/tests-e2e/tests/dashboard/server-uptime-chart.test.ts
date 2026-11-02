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

/** Same shape prometheus_query() returns: one dataset, one label per bucket. */
function uptimePayload(values: (number | null)[]) {
	const start = new Date('2026-08-19T00:00:00')
	return {
		labels: values.map((_, i) =>
			new Date(start.getTime() + i * 3600_000)
				.toISOString()
				.slice(0, 19)
				.replace('T', ' '),
		),
		datasets: [{ name: 'Uptime', values }],
	}
}

async function openUptimeChart(page: Page, values: (number | null)[]) {
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

	// Only uptime carries data; every other chart on the tab stays empty.
	await page.route(
		/\/api\/method\/press\.api\.server\.analytics/,
		async (route) => {
			const url = new URL(route.request().url())
			const query =
				url.searchParams.get('query') ?? route.request().postDataJSON?.()?.query
			const message =
				query === 'database_uptime'
					? uptimePayload(values)
					: { datasets: [], labels: [] }
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ message }),
			})
		},
	)

	await page.goto(
		`/dashboard/servers/${APP_SERVER}/analytics?server=${DATABASE_SERVER}`,
	)

	const chart = page.locator('.chart').first()
	await expect(chart.locator('svg text').first()).toBeVisible({
		timeout: 30000,
	})
	return chart
}

/** Y-axis tick labels of the uptime chart, low to high. */
async function axisTicks(chart: ReturnType<Page['locator']>) {
	const texts = await chart.locator('svg text').allTextContents()
	return texts
		.filter((t) => t.trim().endsWith('%'))
		.map((t) => parseFloat(t))
		.sort((a, b) => a - b)
}

test('uptime chart scales to the dip instead of flatlining at the top', async ({
	page,
}) => {
	// 24 fully-up hours with one hour that lost 5 minutes. As a 0/1 gauge that
	// bucket read 1 and the dip was invisible; as a percentage it is 91.67.
	const values = Array(24).fill(100)
	values[12] = 91.67

	const chart = await openUptimeChart(page, values)
	const ticks = await axisTicks(chart)

	expect(ticks.length, 'y-axis is labelled in percent').toBeGreaterThan(1)
	expect(ticks[ticks.length - 1]).toBe(100)
	// A 0-based axis would squash the dip into the top 8% of the plot.
	expect(ticks[0], 'axis floor sits near the dip, not at zero').toBeGreaterThan(
		50,
	)
})

test('uptime tooltip reports a fully down bucket as 0%', async ({ page }) => {
	const values = Array(24).fill(100)
	values[12] = 0

	const chart = await openUptimeChart(page, values)
	const box = (await chart.boundingBox())!
	// Plot area sits inside the LineChart grid: 50px left, 20px right.
	const plotWidth = box.width - 70
	const x = box.x + 50 + (plotWidth * 12) / (values.length - 1)
	await page.mouse.move(x, box.y + box.height / 2)

	const tooltip = page.getByText(/\d+\s*%/, { exact: false }).last()
	await expect(tooltip).toBeVisible({ timeout: 10000 })
	await expect(tooltip).toHaveText(/(^|\s)0\s*%/)
})
