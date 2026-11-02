import { devices } from '@playwright/test'
import {
	mockAnalytics,
	RANGE_END,
	RANGE_START,
	SITE_NAME,
} from './analytics-fixture'
import { expect, test } from './coverage.fixture'

// A phone: `(pointer: coarse)` matches, which is what turns the drag off.
test.use({ ...devices['Pixel 5'] })

const QUERY = `?start=${RANGE_START.toISOString()}&end=${RANGE_END.toISOString()}`

function rangeFromUrl(url: string) {
	const query = new URL(url).searchParams
	return {
		start: new Date(query.get('start')!).getTime(),
		end: new Date(query.get('end')!).getTime(),
	}
}

/** The plot area of the LineChart: 50px of axis on the left, 20px on the right. */
async function plotBox(page) {
	const chart = page.locator('.chart').first()
	await expect(chart.locator('svg text').first()).toBeVisible({
		timeout: 30000,
	})
	const box = (await chart.boundingBox())!
	return {
		left: box.x + 50,
		width: box.width - 70,
		middle: box.y + box.height / 2,
	}
}

/** Touches the screen at each point, then moves each one to its target. */
async function touchDrag(
	page,
	points: { from: [number, number]; to: [number, number] }[],
) {
	const session = await page.context().newCDPSession(page)
	const at = (index: number, key: 'from' | 'to') => ({
		x: points[index][key][0],
		y: points[index][key][1],
	})
	const all = (key: 'from' | 'to') => points.map((_, index) => at(index, key))

	await session.send('Input.dispatchTouchEvent', {
		type: 'touchStart',
		touchPoints: all('from'),
	})
	for (let step = 1; step <= 10; step++) {
		const fraction = step / 10
		await session.send('Input.dispatchTouchEvent', {
			type: 'touchMove',
			touchPoints: points.map((point) => ({
				x: point.from[0] + (point.to[0] - point.from[0]) * fraction,
				y: point.from[1] + (point.to[1] - point.from[1]) * fraction,
			})),
		})
	}
	await session.send('Input.dispatchTouchEvent', {
		type: 'touchEnd',
		touchPoints: [],
	})
	await session.detach()
}

test('a one finger drag over a site line chart keeps the range', async ({
	page,
}) => {
	await mockAnalytics(page)
	await page.goto(`/dashboard/sites/${SITE_NAME}/insights/analytics${QUERY}`)

	const plot = await plotBox(page)
	// The desktop chart arms drag-to-zoom on its first finished render.
	await page.waitForTimeout(2000)

	await touchDrag(page, [
		{
			from: [plot.left + plot.width * 0.25, plot.middle],
			to: [plot.left + plot.width * 0.75, plot.middle],
		},
	])
	await page.waitForTimeout(1000)

	expect(rangeFromUrl(page.url())).toEqual({
		start: RANGE_START.getTime(),
		end: RANGE_END.getTime(),
	})
})

test('a pinch over a site line chart narrows the range', async ({ page }) => {
	await mockAnalytics(page)
	await page.goto(`/dashboard/sites/${SITE_NAME}/insights/analytics${QUERY}`)

	const plot = await plotBox(page)
	await page.waitForTimeout(2000)

	// Two fingers that move apart around the middle of the plot.
	await touchDrag(page, [
		{
			from: [plot.left + plot.width * 0.45, plot.middle],
			to: [plot.left + plot.width * 0.1, plot.middle],
		},
		{
			from: [plot.left + plot.width * 0.55, plot.middle],
			to: [plot.left + plot.width * 0.9, plot.middle],
		},
	])

	await expect
		.poll(() => rangeFromUrl(page.url()).start, { timeout: 10000 })
		.toBeGreaterThan(RANGE_START.getTime())
	expect(rangeFromUrl(page.url()).end).toBeLessThan(RANGE_END.getTime())
})
