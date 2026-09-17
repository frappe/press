import type { Page, Route } from '@playwright/test'
import { expect, test } from './coverage.fixture'

const SERVER_NAME = 'u1-mumbai.frappe.cloud'

const currentPlan = {
	name: 'Hetzner ccx23',
	title: 'Dedicated',
	price_usd: 170,
	price_inr: 14110,
	vcpu: 4,
	memory: 16384,
	disk: 160,
	instance_type: 'ccx23',
	platform: 'x86_64',
	plan_type: 'dedicated',
	premium: 0,
}

// More CPU on the same disk, so a resize has no disk to upgrade
const sameDiskPlan = {
	...currentPlan,
	name: 'Hetzner cpx41',
	price_usd: 50,
	vcpu: 8,
	instance_type: 'cpx41',
}

const biggerDiskPlan = {
	...currentPlan,
	name: 'Hetzner ccx33',
	price_usd: 280,
	vcpu: 8,
	memory: 32768,
	disk: 240,
	instance_type: 'ccx33',
}

const planTypes = {
	dedicated: {
		name: 'dedicated',
		title: 'Dedicated Instance',
		description: 'Ideal for intense production workloads',
		order_in_list: 0,
	},
}

function server(provider: string, isUnifiedServer: 0 | 1) {
	return {
		name: SERVER_NAME,
		title: 'Test Server',
		status: 'Active',
		cluster: 'Mumbai',
		team: 'test@example.com',
		provider,
		is_unified_server: isUnifiedServer,
		// A unified server shares its name with the database server on the machine
		database_server: SERVER_NAME,
		plan: currentPlan.name,
		current_plan: currentPlan,
		disk_size: currentPlan.disk,
		usage: { vcpu: 0, memory: 0, disk: 0 },
		is_provisioning_press_job_completed: 1,
	}
}

async function mockServer(
	page: Page,
	provider: string,
	isUnifiedServer: 0 | 1,
	rootDiskSize: number = currentPlan.disk,
) {
	await page.route(
		/\/api\/method\/press\.api\.client\.get\b/,
		async (route: Route) => {
			const doctype = new URL(route.request().url()).searchParams.get('doctype')
			if (doctype !== 'Server' && doctype !== 'Database Server')
				return route.continue()

			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ message: server(provider, isUnifiedServer) }),
			})
		},
	)

	await page.route(
		/\/api\/method\/press\.api\.server\.plans\b/,
		async (route: Route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					message: {
						plans: [currentPlan, sameDiskPlan, biggerDiskPlan],
						types: planTypes,
						current_root_disk_size: rootDiskSize,
					},
				}),
			})
		},
	)
}

/** Resolves with the arguments the dialog sends to Server.change_plan */
function captureChangePlan(page: Page) {
	return new Promise<Record<string, unknown>>((resolve) => {
		page.route(
			/\/api\/method\/press\.api\.client\.run_doc_method\b/,
			async (route: Route) => {
				const body = route.request().postDataJSON()
				if (body?.method !== 'change_plan') return route.continue()

				const args =
					typeof body?.args === 'string' ? JSON.parse(body.args) : body?.args
				resolve(args)

				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ message: null }),
				})
			},
		)
	})
}

async function openPlanDialog(page: Page) {
	await page.goto(`/dashboard/servers/${SERVER_NAME}/overview`)
	await page
		.getByRole('button', { name: 'Change', exact: true })
		.first()
		.click({ timeout: 10000 })

	await expect(page.getByRole('button', { name: 'Change plan' })).toBeVisible({
		timeout: 10000,
	})
}

async function selectPlan(page: Page, instanceType: string) {
	await page.locator('button').filter({ hasText: instanceType }).first().click()
	await page.getByRole('button', { name: 'Change plan' }).click()
}

test('opens on the full plan list for a unified Hetzner server', async ({
	page,
}) => {
	await mockServer(page, 'Hetzner', 1)

	await openPlanDialog(page)

	await expect(page.getByText('CPU and Memory only resize')).toBeVisible()
	await expect(page.getByRole('checkbox')).not.toBeChecked()
	// Unchecked, so the plans carry the disk each one includes
	await expect(page.getByText('240 GB')).toBeVisible()
})

test('keeps the disk untouched by default on a Hetzner server that is not unified', async ({
	page,
}) => {
	await mockServer(page, 'Hetzner', 0)

	await openPlanDialog(page)

	await expect(page.getByRole('checkbox')).toBeChecked()
})

test('still offers a DigitalOcean server its disk upgrade', async ({ page }) => {
	await mockServer(page, 'DigitalOcean', 0)
	const changePlan = captureChangePlan(page)

	await openPlanDialog(page)
	await expect(page.getByRole('checkbox')).toBeChecked()

	await page.getByText('CPU and Memory only resize').click()
	await selectPlan(page, biggerDiskPlan.instance_type)

	expect(await changePlan).toMatchObject({
		plan: biggerDiskPlan.name,
		upgrade_disk: true,
	})
})

test('does not ask for a disk upgrade when the plan has the same disk', async ({
	page,
}) => {
	await mockServer(page, 'Hetzner', 1)
	const changePlan = captureChangePlan(page)

	await openPlanDialog(page)
	await selectPlan(page, sameDiskPlan.instance_type)

	expect(await changePlan).toMatchObject({
		plan: sameDiskPlan.name,
		upgrade_disk: false,
	})
})

test('asks for a disk upgrade when the plan has a bigger disk', async ({
	page,
}) => {
	await mockServer(page, 'Hetzner', 1)
	const changePlan = captureChangePlan(page)

	await openPlanDialog(page)
	await selectPlan(page, biggerDiskPlan.instance_type)

	expect(await changePlan).toMatchObject({
		plan: biggerDiskPlan.name,
		upgrade_disk: true,
	})
})

test('measures a disk upgrade against the machine, not against its plan', async ({
	page,
}) => {
	// The volume was expanded on its own, so the machine has more disk than its plan
	await mockServer(page, 'Hetzner', 1, 320)
	const changePlan = captureChangePlan(page)

	await openPlanDialog(page)
	await selectPlan(page, biggerDiskPlan.instance_type)

	expect(await changePlan).toMatchObject({
		plan: biggerDiskPlan.name,
		upgrade_disk: false,
	})
})

test('keeps the disk when the choice is checked', async ({ page }) => {
	await mockServer(page, 'Hetzner', 1)
	const changePlan = captureChangePlan(page)

	await openPlanDialog(page)
	await page.getByText('CPU and Memory only resize').click()
	await selectPlan(page, biggerDiskPlan.instance_type)

	expect(await changePlan).toMatchObject({
		plan: biggerDiskPlan.name,
		upgrade_disk: false,
	})
})
