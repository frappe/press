import type { Page, Route } from '@playwright/test'

export const SITE_NAME = 'test-analytics.fc.frappe.dev'

// A busy site over a long window: every advanced chart fills its top-10 paths
// plus the "Other" bucket, at ~60 buckets (the server caps points at 60 via
// auto_timespan_timegrain). 14 stacked bar charts x 11 series x 60 buckets is
// what makes the page heavy.
const SERIES_PER_CHART = 11
const BUCKETS = 60

export const RANGE_END = new Date('2026-07-20T00:00:00Z')
export const RANGE_START = new Date(
	RANGE_END.getTime() - 15 * 24 * 60 * 60 * 1000,
)
const BUCKET_MS = (RANGE_END.getTime() - RANGE_START.getTime()) / (BUCKETS - 1)

const LABELS = Array.from({ length: BUCKETS }, (_, i) =>
	new Date(RANGE_START.getTime() + i * BUCKET_MS)
		.toISOString()
		.slice(0, 19)
		.replace('T', ' '),
)

/** Shape returned by StackedGroupByChart.run() */
function stackedChart(prefix: string) {
	return {
		labels: LABELS,
		allow_drill_down: false,
		datasets: Array.from({ length: SERIES_PER_CHART }, (_, series) => ({
			path: `/api/method/${prefix}.series_${series}`,
			stack: 'path',
			// Every bucket non-null so echarts emits an element per (series, bucket)
			values: Array.from(
				{ length: BUCKETS },
				(_, i) => 10 + ((i * 7 + series * 13) % 90),
			),
		})),
	}
}

/** Shape returned by get_usage()/get_uptime() consumers: [{value, date}] */
function timeSeries() {
	return LABELS.map((date, i) => ({ date, value: 1000 + (i % 40) * 25 }))
}

const analyticsPayloads: Record<string, unknown> = {
	get: {
		usage_counter: timeSeries(),
		request_count: timeSeries(),
		request_cpu_time: timeSeries(),
		uptime: LABELS.map((date) => ({ date, value: 1 })),
		plan_limit: 10000,
		timegrain: BUCKET_MS / 1000,
	},
	get_request_count_by_path: {
		request_count_by_path: stackedChart('request_count'),
	},
	get_request_duration_by_path: {
		request_duration_by_path: stackedChart('request_duration'),
		// The four slow-path breakdowns bundled into this endpoint
		query_report_run_reports: stackedChart('query_report'),
		run_doc_method_methodnames: stackedChart('run_doc_method'),
		save_docs_doctypes: stackedChart('save_docs_doctypes'),
		save_docs_actions: stackedChart('save_docs_actions'),
	},
	get_average_request_duration_by_path: {
		average_request_duration_by_path: stackedChart('avg_request_duration'),
	},
	get_request_count_by_ip: {
		request_count_by_ip: stackedChart('request_by_ip'),
	},
	get_background_job_count_by_method: {
		background_job_count_by_method: stackedChart('job_count'),
	},
	get_background_job_duration_by_method: {
		background_job_duration_by_method: stackedChart('job_duration'),
		generate_report_reports: stackedChart('generate_report'),
	},
	get_average_background_job_duration_by_method: {
		average_background_job_duration_by_method: stackedChart('avg_job_duration'),
	},
	get_background_job_usage: {
		job_count: timeSeries(),
		job_cpu_time: timeSeries(),
	},
	get_slow_logs_by_query: stackedChart('slow_query'),
}

const siteMock = {
	message: {
		name: SITE_NAME,
		status: 'Active',
		current_plan: null,
		group_public: 0,
	},
}

export async function mockAnalytics(page: Page) {
	await page.route(/\/api\/method\/press\.api\.analytics\./, async (route) => {
		const method = new URL(route.request().url()).pathname.split('.').pop()!
		const payload = analyticsPayloads[method]
		if (payload === undefined) return route.continue()
		await route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ message: payload }),
		})
	})

	await page.route(
		/\/api\/method\/press\.api\.client\.get\b/,
		async (route: Route) => {
			const url = new URL(route.request().url())
			if (url.searchParams.get('doctype') === 'Site') {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify(siteMock),
				})
			} else {
				await route.continue()
			}
		},
	)
}
