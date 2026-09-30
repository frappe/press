import type { Page, Request } from '@playwright/test'
import {
	mockAnalytics,
	RANGE_END,
	RANGE_START,
	SITE_NAME,
} from './analytics-fixture'
import { expect, test } from './coverage.fixture'

const SLOW_QUERY_CARDS = ['#frequent-slow-queries', '#top-slow-queries']

/** frappe-ui sends resource params in the query string or the POST body. */
function normalizeParam(request: Request): string | null {
	const fromUrl = new URL(request.url()).searchParams.get('normalize')
	if (fromUrl !== null) return fromUrl
	try {
		return String(JSON.parse(request.postData() ?? '{}').normalize ?? '')
	} catch {
		return null
	}
}

async function loadAnalyticsPage(page: Page) {
	await page.setViewportSize({ width: 1440, height: 900 })
	await mockAnalytics(page)

	const query = `?start=${RANGE_START.toISOString()}&end=${RANGE_END.toISOString()}`
	await page.goto(`/dashboard/sites/${SITE_NAME}/insights/analytics${query}`)

	// The advanced section is open by default, so no click is necessary.
	for (const card of SLOW_QUERY_CARDS) {
		await expect(page.locator(card)).toBeVisible({ timeout: 30000 })
	}
}

test('the slow query charts ask for normalized queries without being told to', async ({
	page,
}) => {
	test.slow()

	// The raw top-25 is 25 variants of one statement, so the denormalized chart
	// puts almost every query in the "Other" bucket. Normalized is the useful view.
	const normalizeFlags: string[] = []
	page.on('request', (request) => {
		if (!request.url().includes('get_slow_logs_by_query')) return
		const flag = normalizeParam(request)
		if (flag !== null) normalizeFlags.push(flag)
	})

	await loadAnalyticsPage(page)
	await expect.poll(() => normalizeFlags.length).toBeGreaterThanOrEqual(2)

	// Both charts, count and duration, before anyone touches the toggle
	expect(normalizeFlags.every((flag) => flag === 'true' || flag === '1')).toBe(
		true,
	)

	for (const card of SLOW_QUERY_CARDS) {
		// exact, or "Denormalized" matches the substring too
		await expect(
			page
				.locator(card)
				.getByRole('radio', { name: 'Normalized', exact: true }),
		).toBeChecked()
	}
})

test('the slow query toggle sits at the right edge of the card header', async ({
	page,
}) => {
	test.slow()
	await loadAnalyticsPage(page)

	for (const card of SLOW_QUERY_CARDS) {
		const header = page.locator(`${card} > div`).first()
		const toggle = page.locator(card).getByRole('radiogroup')

		const headerBox = (await header.boundingBox())!
		const toggleBox = (await toggle.boundingBox())!

		const gapToRightEdge =
			headerBox.x + headerBox.width - (toggleBox.x + toggleBox.width)

		// The docs and copy icons plus padding take the last ~70px. Before this
		// change two competing auto margins split the free space and left the
		// toggle near the middle of a 1440px-wide header.
		expect(gapToRightEdge, `${card} toggle to right edge`).toBeLessThan(90)
		expect(gapToRightEdge, `${card} toggle overlaps the icons`).toBeGreaterThan(
			0,
		)
	}
})
