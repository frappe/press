import type { Route } from '@playwright/test'
import { expect, test } from './coverage.fixture'

const BENCH = 'bench-0001-000023-f1'
const GROUP = 'bench-0001'
const LOG = 'web.error.log'

// long enough that the log body scrolls, so scroll-to-bottom is observable
const LOG_LINES = Array.from({ length: 500 }, (_, i) => `line ${i + 1}`)
const LOG_TEXT = `${LOG_LINES.join('\n')}\nLAST LINE OF THE LOG`

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

// the group page and its Sites tab, so the test needs no seeded bench
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
			if (!['Bench', 'New Bench Queue', 'Site'].includes(doctype ?? ''))
				return route.continue()

			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(emptyListMock),
			})
		},
	)

	await page.route(/\/api\/method\/press\.api\.bench\.log\b/, async (route) => {
		await route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ message: { [LOG]: LOG_TEXT } }),
		})
	})
}

test('deep link to a bench log opens the logs dialog scrolled to the end', async ({
	page,
}) => {
	await mockGroupPage(page)

	await page.goto(`/dashboard/benches/${BENCH}/logs/${LOG}`)

	await expect(page).toHaveURL(
		`/dashboard/groups/${GROUP}/sites?bench=${BENCH}&log=${LOG}`,
	)
	await expect(page.getByText(`Bench Logs - ${BENCH}`)).toBeVisible({
		timeout: 15000,
	})
	await expect(
		page.getByRole('heading', { name: LOG, exact: true }),
	).toBeVisible()
	await expect(page.getByText('LAST LINE OF THE LOG')).toBeVisible()

	const scrolled = await page
		.locator('pre')
		.first()
		.evaluate((pre) => {
			const body = pre.parentElement as HTMLElement
			return {
				scrollTop: body.scrollTop,
				max: body.scrollHeight - body.clientHeight,
			}
		})
	expect(scrolled.max).toBeGreaterThan(0)
	expect(scrolled.scrollTop).toBeGreaterThan(scrolled.max - 5)
})

test('the sites tab shows no logs dialog without the bench query', async ({
	page,
}) => {
	await mockGroupPage(page)

	await page.goto(`/dashboard/groups/${GROUP}/sites`)

	await expect(page.getByText('Bench Logs -')).not.toBeVisible()
})
