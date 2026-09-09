import type { Route } from '@playwright/test'
import { expect, test } from './coverage.fixture'

const SITE_NAME = 'test-migrate.fc.frappe.dev'
const DESTINATION_IP = '13.234.11.99'

const siteMock = {
	message: {
		name: SITE_NAME,
		status: 'Active',
		// current_plan null prevents the upsell banner from appearing
		current_plan: null,
		group_public: 0,
	},
}

// run_doc_method wraps twice: frappe-ui unwraps the outer `message`, the
// component then reads `.message` off what run_doc_method itself returned
function migrationOptions(hasDomainWithARecord: boolean) {
	return {
		message: {
			message: {
				'In-Place Migrate Site': {
					hidden: false,
					allow_scheduling: false,
					button_label: 'Migrate Site',
					options: {},
				},
				'Move Site To Different Region': {
					hidden: false,
					allow_scheduling: true,
					button_label: 'Move Site',
					options: {
						available_regions: [
							{ name: 'Mumbai', title: 'Mumbai', inbound_ip: DESTINATION_IP },
						],
						has_domain_with_a_record: hasDomainWithARecord,
					},
				},
			},
		},
	}
}

const emptyListMock = { message: [] }

function doctype(route: Route): string | null {
	return route.request().postDataJSON()?.doctype ?? null
}

async function openRegionMigration(
	page: Parameters<typeof test>[1]['page'],
	hasDomainWithARecord: boolean,
) {
	await page.route(
		/\/api\/method\/press\.api\.client\.get\b/,
		async (route) => {
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

	await page.route(
		/\/api\/method\/press\.api\.client\.get_list/,
		async (route) => {
			// Site Action rows are irrelevant, an empty Migrations tab is enough
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(emptyListMock),
			})
		},
	)

	await page.route(
		/\/api\/method\/press\.api\.client\.run_doc_method/,
		async (route) => {
			if (route.request().postDataJSON()?.method === 'get_migration_options') {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify(migrationOptions(hasDomainWithARecord)),
				})
			} else {
				await route.continue()
			}
		},
	)

	await page.goto(`/dashboard/sites/${SITE_NAME}/migrations`)
	await page.getByRole('button', { name: 'Trigger Migration' }).click()

	await expect(page.getByText('Select Migration Type')).toBeVisible({
		timeout: 10000,
	})

	// frappe-ui's Select is a Reka UI listbox, not a native <select>
	await page.getByText('Select Migration Option').click()
	await page
		.getByRole('option', { name: 'Move Site To Different Region' })
		.click()

	await page.getByRole('button', { name: 'Show popup' }).click()
	await page.getByRole('option', { name: 'Mumbai' }).click()
}

test('warns about custom domains on A records with the destination IP', async ({
	page,
}) => {
	await openRegionMigration(page, true)

	const warning = page.getByText(
		'This site has custom domains pointing to an A record',
	)
	await expect(warning).toBeVisible()
	await expect(warning).toContainText(DESTINATION_IP)
	await expect(warning).toContainText(SITE_NAME)
	await expect(page.getByRole('link', { name: 'Read more' })).toHaveAttribute(
		'href',
		'https://docs.frappe.io/cloud/sites/custom-domains',
	)
})

test('shows no A record warning when the site has none', async ({ page }) => {
	await openRegionMigration(page, false)

	await expect(page.getByText('Select Region')).toBeVisible()
	await expect(
		page.getByText('This site has custom domains pointing to an A record'),
	).not.toBeVisible()
})
