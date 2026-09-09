import {
	mockAnalytics,
	RANGE_END,
	RANGE_START,
	SITE_NAME,
} from './analytics-fixture'
import { expect, test } from './coverage.fixture'

/** Start of the range the page holds, read back from its query string. */
function rangeFromUrl(url: string) {
	const query = new URL(url).searchParams
	return {
		start: new Date(query.get('start')!).getTime(),
		end: new Date(query.get('end')!).getTime(),
	}
}

test('dragging over a site line chart narrows the range to the selection', async ({
	page,
}) => {
	await page.setViewportSize({ width: 1440, height: 900 })
	await mockAnalytics(page)

	const query = `?start=${RANGE_START.toISOString()}&end=${RANGE_END.toISOString()}`
	await page.goto(`/dashboard/sites/${SITE_NAME}/insights/analytics${query}`)

	// The first chart on the tab is the Usage Counter line chart.
	const chart = page.locator('.chart').first()
	await expect(chart.locator('svg text').first()).toBeVisible({
		timeout: 30000,
	})

	const box = (await chart.boundingBox())!
	// Plot area sits inside the LineChart grid: 50px left, 20px right.
	const plotStart = box.x + 50
	const plotWidth = box.width - 70
	const y = box.y + box.height / 2

	// The chart arms drag-to-zoom on its first finished render.
	await page.waitForTimeout(2000)
	await page.mouse.move(plotStart + plotWidth * 0.25, y)
	await page.mouse.down()
	await page.mouse.move(plotStart + plotWidth * 0.75, y, { steps: 10 })
	await page.mouse.up()

	// The page keeps its range in the query string, so read it back from there.
	await expect
		.poll(() => rangeFromUrl(page.url()).start, { timeout: 10000 })
		.toBeGreaterThan(RANGE_START.getTime())

	const span = RANGE_END.getTime() - RANGE_START.getTime()
	const tolerance = span / 20
	const zoomed = rangeFromUrl(page.url())

	expect(
		Math.abs(zoomed.start - (RANGE_START.getTime() + span * 0.25)),
	).toBeLessThan(tolerance)
	expect(
		Math.abs(zoomed.end - (RANGE_START.getTime() + span * 0.75)),
	).toBeLessThan(tolerance)
})
