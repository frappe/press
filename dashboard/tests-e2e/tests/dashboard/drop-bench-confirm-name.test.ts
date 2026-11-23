import { expect, test } from './coverage.fixture'

const GROUP_NAME = 'bench-9998'

// HTML collapses the leading spaces, so the dialog shows "Test Bench".
const groupMock = {
	message: {
		name: GROUP_NAME,
		title: '  Test Bench',
		status: 'Active',
		version: 'Version 16',
		public: 0,
		actions_access: {},
		actions: [
			{
				action: 'Drop Bench',
				description: 'Drop the bench',
				button_label: 'Drop',
				doc_method: 'drop',
				group: 'Dangerous Actions',
			},
		],
	},
}

async function openDropBenchDialog(page) {
	await page.route(
		/\/api\/method\/press\.api\.client\.get\b/,
		async (route) => {
			const url = new URL(route.request().url())
			if (url.searchParams.get('doctype') !== 'Release Group') {
				return route.continue()
			}
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
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ message: [] }),
			})
		},
	)

	await page.goto(`/dashboard/groups/${GROUP_NAME}/actions`)
	await page.getByRole('button', { name: 'Drop', exact: true }).click()
	return page.getByRole('dialog')
}

test('drop bench accepts the visible name when the title has leading spaces', async ({
	page,
}) => {
	const dialog = await openDropBenchDialog(page)
	const deleteRequest = page.waitForRequest(
		/\/api\/method\/press\.api\.client\.delete/,
	)
	await page.route(
		/\/api\/method\/press\.api\.client\.delete/,
		async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ message: null }),
			})
		},
	)

	await dialog.getByRole('textbox').fill('Test Bench')
	await dialog.getByRole('button', { name: 'Drop', exact: true }).click()

	const body = (await deleteRequest).postDataJSON()
	expect(body.name).toBe(GROUP_NAME)
	await expect(page.getByText('Bench name does not match')).toHaveCount(0)
})

test('drop bench still rejects a name that does not match', async ({
	page,
}) => {
	const dialog = await openDropBenchDialog(page)

	await dialog.getByRole('textbox').fill('Other Bench')
	await dialog.getByRole('button', { name: 'Drop', exact: true }).click()

	await expect(page.getByText('Bench name does not match')).toBeVisible()
})
