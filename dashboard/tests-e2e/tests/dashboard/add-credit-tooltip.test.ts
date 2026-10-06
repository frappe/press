import type { Page, Route } from '@playwright/test'
import { expect, test } from './coverage.fixture'

const TOOLTIP_TEXT =
	'You can add bulk credits in advance, and it will be adjusted/deducted directly from your monthly invoice.'

async function fulfill(route: Route, message: unknown) {
	await route.fulfill({
		status: 200,
		contentType: 'application/json',
		body: JSON.stringify({ message }),
	})
}

async function openBillingOverview(page: Page) {
	await page.route(
		/\/api\/method\/press\.api\.billing\.upcoming_invoice/,
		(route) => fulfill(route, { available_credits: '₹ 0.00' }),
	)
	await page.route(
		/\/api\/method\/press\.api\.billing\.get_unpaid_invoices/,
		(route) => fulfill(route, []),
	)
	await page.route(
		/\/api\/method\/press\.api\.billing\.total_unpaid_amount/,
		(route) => fulfill(route, 0),
	)
	await page.route(
		/\/api\/method\/press\.api\.account\.get_billing_information/,
		(route) =>
			fulfill(route, {
				billing_name: 'Huzan Kazi',
				address_line1: 'Jogeshwari',
				city: 'Mumbai',
				state: 'Maharashtra',
				country: 'India',
				pincode: '400102',
			}),
	)

	await page.goto('/dashboard/billing')
}

function addCreditButton(page: Page) {
	return page.getByRole('button', { name: 'Add credit' })
}

// getByRole misses this: the visible tooltip is aria-hidden, and reka exposes
// a separate copy of the text to screen readers.
function tooltip(page: Page) {
	return page.locator('[role="tooltip"]')
}

test('hovering add credit explains that credits are adjusted against the invoice', async ({
	page,
}) => {
	await openBillingOverview(page)

	const button = addCreditButton(page)
	await expect(button).toBeVisible({ timeout: 30000 })
	await expect(tooltip(page)).toHaveCount(0)

	await button.hover()

	await expect(tooltip(page)).toHaveText(TOOLTIP_TEXT, { timeout: 10000 })
})

test('the tooltip does not swallow the click that opens the add credit dialog', async ({
	page,
}) => {
	await openBillingOverview(page)

	const button = addCreditButton(page)
	await expect(button).toBeVisible({ timeout: 30000 })

	await button.click()

	await expect(
		page.getByRole('dialog').getByText('Add Credit Balance'),
	).toBeVisible({ timeout: 10000 })
})
