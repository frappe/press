import type { Page, Route } from '@playwright/test'
import { expect, test } from './coverage.fixture'

const APP_SERVER = 'f-test-storage.frappe.cloud'
const DATABASE_SERVER = 'm-test-storage.frappe.cloud'

const plan = {
	name: 'Server Plan 1',
	plan_title: 'Standard',
	price_usd: 100,
	price_inr: 8000,
	vcpu: 2,
	memory: 8192,
	disk: 50,
	premium: 0,
}

function serverDoc(name: string, threshold: number, autoIncrease: number) {
	return {
		name,
		title: name,
		status: 'Active',
		provider: 'AWS EC2',
		is_self_hosted: 0,
		is_unified_server: 0,
		database_server: DATABASE_SERVER,
		replication_server: null,
		secondary_server: null,
		current_plan: plan,
		storage_plan: { price_usd: 0.1, price_inr: 8 },
		usage: { vcpu: 0.2, memory: 4096, disk: 20 },
		disk_size: 50,
		auto_increase_storage: autoIncrease,
		auto_add_storage_min: 25,
		auto_add_storage_max: 250,
		storage_alert_threshold_percent: threshold,
		actions: [],
	}
}

async function fulfill(route: Route, message: unknown) {
	await route.fulfill({
		status: 200,
		contentType: 'application/json',
		body: JSON.stringify({ message }),
	})
}

async function openStorageDialog(
	page: Page,
	{ threshold = 90, autoIncrease = 0 } = {},
) {
	await page.route(
		/\/api\/method\/press\.api\.client\.get\b/,
		async (route) => {
			const doctype = new URL(route.request().url()).searchParams.get('doctype')
			if (doctype === 'Server')
				return fulfill(route, serverDoc(APP_SERVER, threshold, autoIncrease))
			if (doctype === 'Database Server')
				return fulfill(
					route,
					serverDoc(DATABASE_SERVER, threshold, autoIncrease),
				)
			return route.continue()
		},
	)

	await page.goto(`/dashboard/servers/${APP_SERVER}/overview`)

	const configure = page
		.getByRole('button', { name: 'Configure Auto Increase Storage' })
		.first()
	await expect(configure).toBeVisible({ timeout: 30000 })
	await configure.click()

	return page.getByRole('dialog')
}

// frappe-ui renders selects as comboboxes without a usable label, so go by order:
// the alert threshold is the last one in the dialog.
function thresholdSelect(dialog: ReturnType<Page['getByRole']>) {
	return dialog.getByRole('combobox').last()
}

test('the alert threshold can be changed from the storage dialog', async ({
	page,
}) => {
	const dialog = await openStorageDialog(page, { threshold: 90 })

	let submitted: Record<string, unknown> | null = null
	await page.route(
		/\/api\/method\/press\.api\.client\.run_doc_method/,
		async (route) => {
			const body = route.request().postDataJSON()
			if (body?.method === 'configure_auto_add_storage') submitted = body.args
			await fulfill(route, {})
		},
	)

	// The dialog opens on the threshold the server is already alerting at.
	await expect(thresholdSelect(dialog)).toHaveText('90%')

	await thresholdSelect(dialog).click()
	await page.getByRole('option', { name: '75%' }).click()
	await dialog.getByRole('button', { name: 'Confirm' }).click()

	await expect.poll(() => submitted).not.toBeNull()
	expect(submitted).toMatchObject({
		server: APP_SERVER,
		storage_alert_threshold: 75,
	})
})

test('the alert threshold is offered even when auto increase is off', async ({
	page,
}) => {
	const dialog = await openStorageDialog(page, {
		threshold: 80,
		autoIncrease: 0,
	})

	await expect(thresholdSelect(dialog)).toHaveText('80%')

	// The storage increments only apply to auto increase, so they stay hidden.
	await expect(dialog.getByText('Minimum Storage Increase (GB)')).toBeHidden()
	await expect(dialog.getByText('Maximum Storage Increase (GB)')).toBeHidden()
})

test('turning auto increase on reveals the storage increments', async ({
	page,
}) => {
	const dialog = await openStorageDialog(page, {
		threshold: 90,
		autoIncrease: 0,
	})

	await dialog.getByLabel('Enable Auto Increase Storage').check()

	await expect(dialog.getByText('Minimum Storage Increase (GB)')).toBeVisible()
	await expect(dialog.getByText('Maximum Storage Increase (GB)')).toBeVisible()
	await expect(thresholdSelect(dialog)).toHaveText('90%')
})
