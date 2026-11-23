import type { Route } from '@playwright/test'
import { expect, test } from './coverage.fixture'

const GROUP = 'bench-0001'

const groupMock = {
	message: {
		doctype: 'Release Group',
		name: GROUP,
		title: 'Nightly',
		version: 'Nightly',
		team: 'Administrator',
		public: 0,
		status: 'Active',
		apps: [],
		tags: [],
		eol_versions: [],
		tabs_access: {},
		actions_access: {},
		deploy_information: {
			apps: [],
			sites: [],
			removed_apps: [],
			number_of_apps: 0,
			last_deploy: null,
			update_available: false,
			deploy_in_progress: false,
			bench_creation_underway: false,
			has_running_release_pipeline: false,
			can_run_patch_build: false,
		},
	},
}

const emptyListMock = { message: [] }

function listDoctype(route: Route): string | null {
	return route.request().postDataJSON()?.doctype ?? null
}

// the group page and its Config tab, so the test needs no seeded bench
async function mockGroupPage(page: Parameters<typeof test>[1]['page']) {
	await page.route(
		/\/api\/method\/press\.api\.client\.get\b/,
		async (route) => {
			const url = new URL(route.request().url())
			if (url.searchParams.get('doctype') !== 'Release Group')
				return route.continue()

			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(groupMock),
			})
		},
	)

	await page.route(
		/\/api\/method\/press\.api\.client\.get_list/,
		async (route) => {
			const doctype = listDoctype(route)
			const mocked = ['Common Site Config', 'Release Group App', 'Bench']
			if (!mocked.includes(doctype ?? '')) return route.continue()

			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(emptyListMock),
			})
		},
	)
}

test('a list route names itself in the tab title', async ({ page }) => {
	await page.goto('/dashboard/sites')

	await expect(page).toHaveTitle('Sites - Frappe Cloud')
})

test('a nested route names its section and its page', async ({ page }) => {
	await page.goto('/dashboard/billing/invoices')

	await expect(page).toHaveTitle('Billing - Invoices - Frappe Cloud')
})

test('a detail tab names the document and the tab', async ({ page }) => {
	await mockGroupPage(page)

	await page.goto(`/dashboard/groups/${GROUP}/bench-config`)

	// the document name shows until the document loads, then its title
	await expect(page).toHaveTitle('Nightly - Config - Frappe Cloud', {
		timeout: 15000,
	})
})

test('a detail tab retitles the page on a tab switch', async ({ page }) => {
	await mockGroupPage(page)

	await page.goto(`/dashboard/groups/${GROUP}/bench-config`)
	await expect(page).toHaveTitle('Nightly - Config - Frappe Cloud', {
		timeout: 15000,
	})

	await page.getByRole('tab', { name: 'Apps' }).click()

	await expect(page).toHaveTitle('Nightly - Apps - Frappe Cloud')
})
