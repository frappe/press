import { expect, test } from './coverage.fixture'

const TITLE = 'Frappe v16.50 is out'
const BLOG_URL =
	'https://frappe.io/blog/product-updates/announcing-framework-erpnext-and-hrms-v1650'

// Same shape as get_v16_50_release_banner, so the test does not depend on the date or on v16 sites
const banner = {
	name: 'v16-50-release',
	type: 'Info',
	title: TITLE,
	message: 'A major update to v16. Update your bench to get it.',
	help_url: BLOG_URL,
	is_dismissible: 1,
	is_global: 1,
	cluster: [],
	server: [],
	site: [],
}

test('v16 release banner shows on the sites list, opens the blog and stays dismissed after a reload', async ({
	page,
	context,
}) => {
	await page.route(
		/\/api\/method\/press\.api\.account\.get_user_banners/,
		(route) => route.fulfill({ json: { message: [banner] } }),
	)
	await context.route(BLOG_URL, (route) => route.fulfill({ body: 'blog' }))
	const dismissCalls: string[] = []
	page.on('request', (request) => {
		if (request.url().includes('press.api.account.dismiss_banner'))
			dismissCalls.push(request.url())
	})

	await page.goto('/dashboard/sites')
	const alert = page.locator('div.rounded-md', { hasText: TITLE }).first()
	await expect(alert).toBeVisible({ timeout: 15000 })

	const [popup] = await Promise.all([
		context.waitForEvent('page'),
		alert.getByRole('button', { name: 'Open help' }).click(),
	])
	await popup.waitForURL(BLOG_URL, { waitUntil: 'commit' })
	await popup.close()

	await alert.getByRole('button').last().click()
	await expect(page.getByText(TITLE)).not.toBeVisible()

	const bannersLoaded = page.waitForResponse(/get_user_banners/)
	await page.reload()
	await bannersLoaded
	// Let Vue render the banners from that response before the check
	await page.evaluate(() => new Promise(requestAnimationFrame))
	await expect(page.getByText(TITLE)).not.toBeVisible()
	// is_global banners keep the dismissal in local storage, so no DB call
	expect(dismissCalls).toEqual([])
})
