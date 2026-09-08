import type { Page, Route } from '@playwright/test'
import { expect, test } from './coverage.fixture'

const APP_SERVER = 'f-tooltip.frappe.cloud'
const DATABASE_SERVER = 'm-tooltip.frappe.cloud'

// Timestamps are stored in IST, so pin the browser timezone to keep the
// formatted tooltip the same wherever the suite runs. The wider viewport keeps
// the Date column on screen, so hovering it doesn't scroll the row first.
test.use({ timezoneId: 'Asia/Kolkata', viewport: { width: 1600, height: 900 } })

const job = {
	name: 'job-1',
	job_type: 'Backup Site',
	status: 'Pending',
	site: 'shared-usd50.fc.dev',
	duration: null,
	owner: 'Administrator',
	creation: '2026-06-08 16:05:00',
	job_id: 1,
	end: null,
}

const planChange = {
	name: 'plan-change-1',
	from_plan: 'DB - Starter 2vCPU 4GB',
	to_plan: 'DB - Standard 4vCPU 8GB',
	type: 'Upgrade',
	timestamp: '2026-06-08 16:05:00',
	owner: 'Administrator',
	document_type: 'Database Server',
}

function serverDoc(name: string) {
	return {
		name,
		title: name,
		status: 'Active',
		provider: 'AWS EC2',
		is_self_hosted: 0,
		is_unified_server: 0,
		database_server: DATABASE_SERVER,
		replication_server: null,
		secondary_server: null,
		current_plan: null,
		storage_plan: { price_usd: 0.1, price_inr: 8 },
		usage: {},
		disk_size: 50,
		actions: [],
	}
}

async function fulfill(route: Route, message: unknown) {
	await route.fulfill({
		status: 200,
		contentType: 'application/json',
		body: JSON.stringify({ message }),
	})
}

async function openServerTab(page: Page, tab: string) {
	await page.route(
		/\/api\/method\/press\.api\.client\.get\b/,
		async (route) => {
			const doctype = new URL(route.request().url()).searchParams.get('doctype')
			if (doctype === 'Server') return fulfill(route, serverDoc(APP_SERVER))
			if (doctype === 'Database Server')
				return fulfill(route, serverDoc(DATABASE_SERVER))
			return route.continue()
		},
	)

	await page.route(
		/\/api\/method\/press\.api\.client\.get_list/,
		async (route) => {
			const doctype = route.request().postDataJSON()?.doctype
			if (doctype === 'Plan Change') return fulfill(route, [planChange])
			if (doctype === 'Agent Job') return fulfill(route, [job])
			return fulfill(route, [])
		},
	)

	await page.goto(`/dashboard/servers/${APP_SERVER}/${tab}`)
}

// getByRole misses these: the visible tooltip is aria-hidden, and reka exposes
// a separate copy of the text to screen readers.
function tooltip(page: Page) {
	return page.locator('[role="tooltip"]')
}

async function hoverTheDate(page: Page) {
	const date = page.getByText('ago', { exact: false }).first()
	await expect(date).toBeVisible({ timeout: 30000 })
	await date.hover()
}

test('hovering a plan change date shows the exact date and time', async ({
	page,
}) => {
	await openServerTab(page, 'plan-history')

	await hoverTheDate(page)

	await expect(tooltip(page)).toHaveText('Monday, June 8, 2026 4:05 PM', {
		timeout: 10000,
	})
})

test('hovering a job date shows the exact date and time', async ({ page }) => {
	await openServerTab(page, 'jobs')

	await hoverTheDate(page)

	await expect(tooltip(page)).toHaveText('Monday, June 8, 2026 4:05 PM', {
		timeout: 10000,
	})
})
