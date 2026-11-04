import type { Page, Route } from '@playwright/test'
import { expect, test } from './coverage.fixture'

const SERVER = 'f-test-app.frappe.cloud'

const serverDoc = {
	name: SERVER,
	title: 'Test Server',
	status: 'Active',
	is_self_hosted: 0,
	malware_scan: { enabled: 0, has_enough_ram: false, last_scan: null },
}

const firewallDoc = { name: SERVER, enabled: 0, rules: [] }

async function mockServerAndFirewall(page: Page) {
	await page.route(
		/\/api\/method\/press\.api\.client\.get\b/,
		async (route) => {
			const doctype = new URL(route.request().url()).searchParams.get('doctype')
			const doc =
				doctype === 'Server'
					? serverDoc
					: doctype === 'Server Firewall'
						? firewallDoc
						: null
			if (!doc) return route.continue()
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ message: doc }),
			})
		},
	)
}

async function mockFirewallSave(
	page: Page,
	respond: (route: Route) => Promise<void>,
) {
	await page.route(
		/\/api\/method\/press\.api\.client\.set_value/,
		async (route) => {
			if (route.request().postDataJSON()?.doctype !== 'Server Firewall') {
				return route.continue()
			}
			await respond(route)
		},
	)
}

async function enableFirewall(page: Page) {
	await page.goto(`/dashboard/servers/${SERVER}/security`)
	const enabled = page.getByLabel('Enabled')
	await expect(enabled).toBeVisible({ timeout: 30000 })
	await enabled.check()
}

test('saving the firewall shows progress, then says changes take a few minutes', async ({
	page,
}) => {
	let release = () => {}
	const held = new Promise<void>((resolve) => {
		release = resolve
	})
	await mockServerAndFirewall(page)
	await mockFirewallSave(page, async (route) => {
		await held
		await route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ message: { ...firewallDoc, enabled: 1 } }),
		})
	})

	await enableFirewall(page)
	const save = page.getByRole('button', { name: 'Save' })
	await save.click()

	await expect(page.getByText('Saving firewall settings…')).toBeVisible()
	await expect(
		save,
		'a second click cannot send a duplicate save',
	).toBeDisabled()

	release()
	await expect(
		page.getByText(
			'Firewall settings saved. They take a few minutes to apply.',
		),
	).toBeVisible()
})

test('a rejected firewall save shows the reason from the server', async ({
	page,
}) => {
	await mockServerAndFirewall(page)
	await mockFirewallSave(page, (route) =>
		route.fulfill({
			status: 417,
			contentType: 'application/json',
			body: JSON.stringify({
				exc_type: 'ValidationError',
				_server_messages: JSON.stringify([
					JSON.stringify({ message: 'Invalid port 99999' }),
				]),
			}),
		}),
	)

	await enableFirewall(page)
	await page.getByRole('button', { name: 'Save' }).click()

	await expect(page.getByText('Invalid port 99999')).toBeVisible()
	await expect(
		page.getByText(
			'Firewall settings saved. They take a few minutes to apply.',
		),
	).not.toBeVisible()
})

test('the firewall warns that a rule can cut off access, without a banner', async ({
	page,
}) => {
	await mockServerAndFirewall(page)
	await page.goto(`/dashboard/servers/${SERVER}/security`)

	await expect(page.getByLabel('Enabled')).toBeVisible({ timeout: 30000 })
	await expect(
		page.getByText('A wrong rule can cut off your own access to the server.'),
	).toBeVisible()
	await expect(
		page.getByText('mis-configuring firewall rules'),
	).not.toBeVisible()
})
