import type { Page, Route } from '@playwright/test'
import {
	cpuData,
	emptyData,
	singleSeriesData,
} from '../../mocks/server-charts/analytics'
import { expect, test } from './coverage.fixture'

const SERVER_NAME = 'f1-mumbai.frappe.cloud'

const serverMock = {
	message: {
		name: SERVER_NAME,
		title: 'f1-mumbai',
		status: 'Active',
		is_unified_server: 0,
		// no database_server / replication_server -> single server, no dropdown
		database_server: null,
		replication_server: null,
		team: 'test-team',
	},
}

// Read the chart name from either the query string (GET) or the body (POST),
// since frappe-ui may send method params either way.
function chartQuery(route: Route): string | null {
	const fromQuery = new URL(route.request().url()).searchParams.get('query')
	if (fromQuery) return fromQuery
	try {
		return route.request().postDataJSON()?.query ?? null
	} catch {
		return null
	}
}

async function mockServerDoc(page: Page) {
	await page.route(
		/\/api\/method\/press\.api\.client\.get\b/,
		async (route) => {
			const doctype = new URL(route.request().url()).searchParams.get('doctype')
			if (doctype === 'Server') {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify(serverMock),
				})
			} else {
				await route.continue()
			}
		},
	)
}

// Route every chart query. `responses` maps a chart name to its payload; any
// chart not listed falls back to a small healthy CPU-shaped response so the
// page never blocks on a missing mock.
async function mockAnalytics(
	page: Page,
	responses: Record<string, unknown> = {},
) {
	await page.route(
		/\/api\/method\/press\.api\.server\.analytics/,
		async (route) => {
			const query = chartQuery(route) ?? 'cpu'
			const payload = responses[query] ?? cpuData()
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ message: payload }),
			})
		},
	)
}

async function gotoAnalytics(page: Page) {
	await page.goto(`/dashboard/servers/${SERVER_NAME}/analytics`)
}

function cpuCard(page: Page) {
	// AnalyticsCard sets id="cpu" (slugified title) — a stable scope.
	return page.locator('#cpu')
}

test('renders the CPU chart with its series when analytics data is present', async ({
	page,
}) => {
	await mockServerDoc(page)
	await mockAnalytics(page, { cpu: cpuData() })

	await gotoAnalytics(page)

	// Card heading confirms the analytics tab mounted.
	await expect(cpuCard(page)).toBeVisible({ timeout: 15000 })

	// echarts uses the SVG renderer, so the line series are real DOM nodes.
	// Scope to the VChart element (class="chart") so we don't match the
	// lucide link icon in the card header.
	const chart = cpuCard(page).locator('.chart svg')
	await expect(chart).toBeVisible()
	// One <path> per CPU mode (8) plus axis/grid paths -> at least the 8 lines.
	await expect
		.poll(async () => chart.locator('path').count(), { timeout: 15000 })
		.toBeGreaterThanOrEqual(8)

	// Data is present, so the empty state must not show in the CPU card.
	await expect(cpuCard(page).getByText('No usage yet')).toHaveCount(0)
})

test('requests CPU analytics with a start and end time range', async ({
	page,
}) => {
	await mockServerDoc(page)

	const cpuRequest = page.waitForRequest((request) => {
		if (!/press\.api\.server\.analytics/.test(request.url())) return false
		const fromQuery = new URL(request.url()).searchParams.get('query')
		let query = fromQuery
		if (!query) {
			try {
				query = request.postDataJSON()?.query ?? null
			} catch {
				query = null
			}
		}
		return query === 'cpu'
	})

	await mockAnalytics(page, { cpu: cpuData() })
	await gotoAnalytics(page)

	const request = await cpuRequest
	const url = new URL(request.url())
	const params = (() => {
		try {
			return request.postDataJSON() ?? {}
		} catch {
			return {}
		}
	})()
	const start = url.searchParams.get('start') ?? params.start
	const end = url.searchParams.get('end') ?? params.end

	// The chart must drive the range-based API (the old `duration` param regressed
	// the timegrain). Both ends of the window must be sent.
	expect(start, 'start time must be sent').toBeTruthy()
	expect(end, 'end time must be sent').toBeTruthy()
})

test('shows the empty state when the CPU chart has no data', async ({
	page,
}) => {
	await mockServerDoc(page)
	await mockAnalytics(page, {
		cpu: emptyData(),
		// keep other cards populated so we know the page rendered
		memory: singleSeriesData(),
	})

	await gotoAnalytics(page)

	await expect(cpuCard(page)).toBeVisible({ timeout: 15000 })
	// The empty CPU card surfaces the no-data message rather than a 0-line chart.
	await expect(cpuCard(page).getByText('No usage yet')).toBeVisible()
})
