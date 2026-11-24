import { expect, test } from './coverage.fixture'

const GROUP = 'bench-9997'

const json = (message: unknown) => ({
	status: 200,
	contentType: 'application/json',
	body: JSON.stringify({ message }),
})

test('Add Site on the bench list sends a plan with the new site', async ({
	page,
}) => {
	await page.route(/\/api\/method\/press\.api\.client\.get_list/, (route) => {
		const doctype = route.request().postDataJSON()?.doctype
		if (doctype !== 'Release Group') return route.fulfill(json([]))
		return route.fulfill(
			json([
				{
					name: GROUP,
					title: 'Private Bench',
					version: 'Version 15',
					site_count: 0,
					active_benches: 1,
					public: 0,
					apps: [{ app: 'frappe' }],
				},
			]),
		)
	})
	await page.route(
		/\/api\/method\/press\.api\.site\.options_for_new/,
		(route) =>
			route.fulfill(
				json({
					domain: 'frappe.cloud',
					versions: [
						{
							group: {
								name: GROUP,
								clusters: [{ name: 'Mumbai' }],
								bench_app_sources: [],
							},
						},
					],
				}),
			),
	)
	await page.route(/\/api\/method\/press\.api\.site\.get_site_plans/, (route) =>
		route.fulfill(
			json([
				{
					name: 'Plan 10',
					price_usd: 10,
					price_inr: 800,
					cpu_time_per_day: 1,
					max_database_usage: 1024,
					max_storage_usage: 5120,
					private_benches: 1,
					dedicated_server_plan: 0,
					restricted_plan: 0,
					clusters: [],
					allowed_apps: [],
					bench_versions: [],
					cloud_providers: [],
				},
			]),
		),
	)
	const insertRequest = page.waitForRequest(
		/\/api\/method\/press\.api\.client\.insert/,
	)
	await page.route(/\/api\/method\/press\.api\.client\.insert/, (route) =>
		route.fulfill(json({ name: 'unbilled.frappe.cloud' })),
	)

	await page.goto('/dashboard/groups')
	const row = page.locator('.bench-grid', {
		has: page.getByRole('link', { name: 'Private Bench' }),
	})
	await row.getByRole('button').last().click()
	await page.getByRole('menuitem', { name: 'Add Site' }).click()
	const dialog = page.getByRole('dialog')
	await dialog.getByRole('button', { name: 'Next' }).click()
	await dialog.getByPlaceholder('Enter site name').fill('unbilled')
	await dialog.getByRole('button', { name: 'Next' }).click()
	await dialog.getByText('compute hour').click()
	await dialog.getByRole('button', { name: 'Add and deploy site' }).click()

	const { doc } = (await insertRequest).postDataJSON()
	expect(doc.subdomain).toBe('unbilled')
	// Without a plan the site gets no subscription and is never billed.
	expect(doc.subscription_plan).toBe('Plan 10')
})
