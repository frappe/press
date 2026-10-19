import type { Page, Route } from '@playwright/test'
import { expect, test } from './coverage.fixture'

const INVOICE_NAME = 'INV-TEST-SNAPSHOTS'

// Two snapshot lines: the invoice dialog used to cache only the last
// requested snapshot, so it requested the other one on every render
const snapshots: Record<string, string> = {
	'snap-test-1': 'f1-mumbai.frappe.cloud',
	'snap-test-2': 'f2-mumbai.frappe.cloud',
}

const invoice = {
	name: INVOICE_NAME,
	type: 'Subscription',
	status: 'Unpaid',
	currency: 'INR',
	period_start: '2026-09-01',
	period_end: '2026-09-30',
	due_date: '2026-10-01',
	total: 200,
	amount_due: 200,
	amount_due_with_tax: 200,
	applied_credits: 0,
	gst: 0,
	total_discount_amount: 0,
	items: Object.keys(snapshots).map((name, i) => ({
		idx: i + 1,
		document_type: 'Server Snapshot',
		document_name: name,
		rate: 100,
		quantity: 1,
		amount: 100,
	})),
}

function getParams(route: Route): Record<string, string> {
	const request = route.request()
	if (request.method() === 'GET') {
		return Object.fromEntries(new URL(request.url()).searchParams)
	}
	return request.postDataJSON() ?? {}
}

function fulfill(route: Route, message: unknown) {
	return route.fulfill({
		status: 200,
		contentType: 'application/json',
		body: JSON.stringify({ message }),
	})
}

async function mockInvoice(page: Page) {
	const snapshotRequests: string[] = []

	await page.route(
		/\/api\/method\/press\.api\.client\.get_list\b/,
		async (route: Route) => {
			if (getParams(route).doctype !== 'Invoice') return route.continue()
			await fulfill(route, [invoice])
		},
	)

	await page.route(
		/\/api\/method\/press\.api\.client\.get\b/,
		async (route: Route) => {
			const { doctype, name } = getParams(route)
			if (doctype === 'Invoice') return fulfill(route, invoice)
			if (doctype !== 'Server Snapshot') return route.continue()

			snapshotRequests.push(name)
			await fulfill(route, { name, app_server: snapshots[name] })
		},
	)

	return snapshotRequests
}

test('shows the server of each snapshot and fetches it once', async ({
	page,
}) => {
	const snapshotRequests = await mockInvoice(page)

	await page.goto('/dashboard/billing/invoices')
	await page.getByText('September 2026').click()

	const serverCells = page
		.getByRole('dialog')
		.getByRole('cell', { name: /\.frappe\.cloud$/ })
	await expect(serverCells).toHaveCount(2, { timeout: 10000 })

	// Give a render loop time to show itself
	await page.waitForTimeout(2000)

	// Each row shows the server of its own snapshot
	await expect.soft(serverCells).toHaveText(Object.values(snapshots))
	expect(snapshotRequests.sort()).toEqual(Object.keys(snapshots).sort())
})
