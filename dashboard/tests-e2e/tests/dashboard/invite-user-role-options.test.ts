import { expect, test } from './coverage.fixture'

// more roles than the default page of 20
const roles = Array.from({ length: 25 }, (_, index) => ({
	name: `role-${String(index + 1).padStart(2, '0')}`,
	title: `Role ${String(index + 1).padStart(2, '0')}`,
}))

test('invite user dialog lists every role, sorted by title, when the team has more than 20', async ({
	page,
}) => {
	let roleRequest: { order_by?: string } | undefined
	await page.route(
		/\/api\/method\/press\.api\.client\.get_list/,
		async (route) => {
			const body = route.request().postDataJSON()
			if (body?.doctype !== 'Press Role') return route.continue()
			roleRequest = body

			// answer like the server, which returns at most `limit` rows
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ message: roles.slice(0, body.limit ?? 20) }),
			})
		},
	)

	await page.goto('/dashboard/settings/team')
	await page.getByRole('button', { name: 'Invite User' }).click()

	// fill replaces the preselected Admin
	await page.getByRole('dialog').getByRole('combobox').fill('Role 25')

	await expect(page.getByRole('option', { name: 'Role 25' })).toBeVisible()
	// the mock ignores order, so check the dialog asks for it
	expect(roleRequest?.order_by).toBe('title asc')
})
