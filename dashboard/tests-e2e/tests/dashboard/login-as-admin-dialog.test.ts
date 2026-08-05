import { expect, test } from './coverage.fixture'

const SITE_NAME = 'test-login.fc.frappe.dev'

const siteMock = {
	message: {
		name: SITE_NAME,
		status: 'Active',
		// current_plan null prevents the upsell banner from appearing
		current_plan: null,
		group_public: 0,
		setup_wizard_complete: 1,
		// breadcrumbs for a desk user link to the server and bench group
		server: 'f1.local.frappe.dev',
		server_title: 'Server 1',
		group: 'bench-0001',
		group_title: 'Bench 1',
	},
}

const emptyListMock = { message: [] }

async function openLoginAsAdminDialog(page) {
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
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(emptyListMock),
			})
		},
	)

	await page.goto(`/dashboard/sites/${SITE_NAME}/overview`)
	await page.getByRole('button', { name: 'Options' }).click()
	await page.getByText('Login As Administrator').click()

	return page.getByRole('dialog').getByRole('textbox')
}

test('login as admin dialog focuses the reason field with a prefilled default', async ({
	page,
}) => {
	const reason = await openLoginAsAdminDialog(page)

	await expect(reason).toBeFocused()
	await expect(reason).toHaveValue('Investigating ')

	// caret sits at the end, so typing appends to the default
	await page.keyboard.type('12345')
	await expect(reason).toHaveValue('Investigating 12345')
})

test('login as admin dialog submits on ctrl+enter from the reason field', async ({
	page,
}) => {
	const reason = await openLoginAsAdminDialog(page)

	const loginRequest = page.waitForRequest(
		/\/api\/method\/press\.api\.client\.run_doc_method/,
	)
	await page.route(
		/\/api\/method\/press\.api\.client\.run_doc_method/,
		async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ message: { message: 'https://example.com' } }),
			})
		},
	)

	await reason.press('Control+Enter')

	const body = (await loginRequest).postDataJSON()
	expect(body.method).toBe('login_as_admin')
	expect(body.args.reason).toBe('Investigating ')
})
