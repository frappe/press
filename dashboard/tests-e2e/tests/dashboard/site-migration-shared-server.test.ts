import type { Page, Route } from '@playwright/test'
import { expect, test } from './coverage.fixture'

const SITE_NAME = 'test-migrate.fc.frappe.dev'
const SHORTCUT = 'Move to Another Shared Server'
const DESTINATION = {
	name: 'f4-mumbai.fc.frappe.dev',
	title: 'Mumbai - Shared Server 4',
	free_memory_percent: 62,
	idle_cpu_percent: 78,
	free_disk_percent: 71,
	bench: 'bench-0001-000002-f4-mumbai',
	needs_deploy: false,
}

// Mirrors `frappe.throw` from Site.pick_shared_server_for_migration. frappe-ui
// parses `_server_messages` into the error the dialog prints.
const noRoomError = {
	exc_type: 'ValidationError',
	_server_messages: JSON.stringify([
		JSON.stringify({
			message:
				'No other shared server in Mumbai has room for this site right now.' +
				' Please try again later, or move the site to a different region.',
			title: 'Message',
		}),
	]),
}

// The Actions tab only draws a group that has at least one action in it
const siteActions = [
	{
		action: 'Clear cache',
		description: 'Clear cache on your site',
		button_label: 'Clear',
		doc_method: 'clear_site_cache',
	},
]

function siteMock(isDedicatedServer: boolean) {
	return {
		message: {
			name: SITE_NAME,
			status: 'Active',
			// current_plan null prevents the upsell banner from appearing
			current_plan: null,
			// A site on a dedicated server is on a bench of its own
			group_public: isDedicatedServer ? 0 : 1,
			is_dedicated_server: isDedicatedServer ? 1 : 0,
			server: 'f1-mumbai.fc.frappe.dev',
			cluster: { title: 'Mumbai', image: '' },
			actions: siteActions,
		},
	}
}

// run_doc_method wraps twice: frappe-ui unwraps the outer `message`, the
// component then reads `.message` off what run_doc_method itself returned
function migrationOptions(isDedicatedServer: boolean) {
	return {
		message: {
			message: {
				'In-Place Migrate Site': {
					hidden: false,
					allow_scheduling: false,
					button_label: 'Migrate Site',
					options: {},
				},
				'Move Site To Another Shared Server': {
					hidden: isDedicatedServer,
					allow_scheduling: true,
					button_label: 'Move Site',
					options: { region: 'Mumbai', cooldown_days: 60 },
				},
			},
		},
	}
}

function migrationTarget(needsDeploy: boolean) {
	return {
		message: {
			message: {
				region: 'Mumbai',
				destination_server: needsDeploy
					? { ...DESTINATION, bench: null, needs_deploy: true }
					: DESTINATION,
			},
		},
	}
}

function docMethod(route: Route): string | null {
	return route.request().postDataJSON()?.method ?? null
}

async function mockSite(
	page: Page,
	{ isDedicatedServer = false, hasRoom = true, needsDeploy = false } = {},
) {
	await page.route(
		/\/api\/method\/press\.api\.client\.get\b/,
		async (route) => {
			const url = new URL(route.request().url())
			if (url.searchParams.get('doctype') === 'Site') {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify(siteMock(isDedicatedServer)),
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
				body: JSON.stringify({ message: [] }),
			})
		},
	)

	await page.route(
		/\/api\/method\/press\.api\.client\.run_doc_method/,
		async (route) => {
			const method = docMethod(route)
			if (method === 'get_migration_options') {
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify(migrationOptions(isDedicatedServer)),
				})
			} else if (method === 'get_shared_server_migration_target') {
				await route.fulfill({
					status: hasRoom ? 200 : 417,
					contentType: 'application/json',
					body: JSON.stringify(
						hasRoom ? migrationTarget(needsDeploy) : noRoomError,
					),
				})
			} else {
				await route.continue()
			}
		},
	)
}

function shortcutRow(page: Page) {
	return page
		.locator('div.py-3')
		.filter({ has: page.getByRole('heading', { name: SHORTCUT }) })
}

test('moves a site on a shared server to the shared server with room', async ({
	page,
}) => {
	await mockSite(page)
	await page.goto(`/dashboard/sites/${SITE_NAME}/actions`)

	await expect(page.getByRole('heading', { name: SHORTCUT })).toBeVisible({
		timeout: 30000,
	})
	// The neighbouring row is about leaving shared hosting, and says so
	await expect(
		page.getByRole('heading', { name: 'Move to a Private Bench' }),
	).toBeVisible()
	// The 60-day limit belongs in the dialog, not in this row
	await expect(shortcutRow(page).getByText('60 days')).toHaveCount(0)
	await shortcutRow(page).getByRole('button', { name: 'Move Site' }).click()

	// The shortcut lands on the Migrations tab with the type already chosen
	await expect(page).toHaveURL(new RegExp(`/sites/${SITE_NAME}/migrations`))
	const dialog = page.getByRole('dialog', { name: 'Migrate Site' })
	await expect(dialog).toBeVisible()
	await expect(
		dialog.getByText('Move Site To Another Shared Server'),
	).toBeVisible()

	// The destination is picked for the site, with the room it has to spare
	await expect(dialog.getByText(DESTINATION.title)).toBeVisible()
	await expect(
		dialog.getByText('This is the shared server in Mumbai'),
	).toBeVisible()
	await expect(
		dialog.getByText('only once every 60 days'),
	).toBeVisible()
	await expect(dialog.getByText('Memory free: 62%')).toBeVisible()
	await expect(dialog.getByText('CPU idle: 78%')).toBeVisible()
	await expect(dialog.getByText('Disk free: 71%')).toBeVisible()
	await expect(dialog.getByRole('button', { name: 'Move Site' })).toBeEnabled()
})

test('says the bench gets deployed when the server does not run it yet', async ({
	page,
}) => {
	await mockSite(page, { needsDeploy: true })
	await page.goto(`/dashboard/sites/${SITE_NAME}/actions`)

	await expect(page.getByRole('heading', { name: SHORTCUT })).toBeVisible({
		timeout: 30000,
	})
	await shortcutRow(page).getByRole('button', { name: 'Move Site' }).click()

	const dialog = page.getByRole('dialog', { name: 'Migrate Site' })
	await expect(dialog.getByText(DESTINATION.title)).toBeVisible()
	await expect(
		dialog.getByText('Your bench does not run there yet, so we deploy it first'),
	).toBeVisible()
	// One click still does the whole thing
	await expect(dialog.getByRole('button', { name: 'Move Site' })).toBeEnabled()
})

test('leaves out the deploy note when the server already runs the bench', async ({
	page,
}) => {
	await mockSite(page)
	await page.goto(`/dashboard/sites/${SITE_NAME}/actions`)

	await expect(page.getByRole('heading', { name: SHORTCUT })).toBeVisible({
		timeout: 30000,
	})
	await shortcutRow(page).getByRole('button', { name: 'Move Site' }).click()

	const dialog = page.getByRole('dialog', { name: 'Migrate Site' })
	await expect(dialog.getByText(DESTINATION.title)).toBeVisible()
	await expect(dialog.getByText('so we deploy it first')).toHaveCount(0)
})

test('offers no shared server move to a site on a dedicated server', async ({
	page,
}) => {
	await mockSite(page, { isDedicatedServer: true })
	await page.goto(`/dashboard/sites/${SITE_NAME}/actions`)

	await expect(page.getByText('General Actions')).toBeVisible({
		timeout: 30000,
	})
	await expect(page.getByRole('heading', { name: SHORTCUT })).toHaveCount(0)
	// It keeps the bench move, worded for a site that is already on its own bench
	await expect(
		page.getByRole('heading', { name: 'Move to a Different Bench or Server' }),
	).toBeVisible()
})

test('blocks the move when no shared server has room for the site', async ({
	page,
}) => {
	await mockSite(page, { hasRoom: false })
	await page.goto(`/dashboard/sites/${SITE_NAME}/actions`)

	await expect(page.getByRole('heading', { name: SHORTCUT })).toBeVisible({
		timeout: 30000,
	})
	await shortcutRow(page).getByRole('button', { name: 'Move Site' }).click()

	const dialog = page.getByRole('dialog', { name: 'Migrate Site' })
	await expect(
		dialog.getByText('No other shared server in Mumbai has room'),
	).toBeVisible()
	await expect(dialog.getByRole('button', { name: 'Move Site' })).toBeDisabled()
})
