import { expect, test } from './coverage.fixture'

const BENCH = 'bench-0001-000023-f1'
const GROUP = 'bench-0001'
const LOG = 'web.error.log'

// long enough that the log body scrolls, so scroll-to-bottom is observable
const LOG_LINES = Array.from({ length: 500 }, (_, i) => `line ${i + 1}`)
const LOG_TEXT = `${LOG_LINES.join('\n')}\nLAST LINE OF THE LOG`

test('deep link to a bench log opens the logs dialog scrolled to the end', async ({
	page,
}) => {
	await page.route(/\/api\/method\/press\.api\.bench\.log\b/, async (route) => {
		await route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ message: { [LOG]: LOG_TEXT } }),
		})
	})

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
	await page.goto(`/dashboard/groups/${GROUP}/sites`)

	await expect(page.getByText('Bench Logs -')).not.toBeVisible()
})
