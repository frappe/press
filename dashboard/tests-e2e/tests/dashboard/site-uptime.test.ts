import { mockAnalytics, SITE_NAME } from './analytics-fixture'
import { expect, test } from './coverage.fixture'

const UPTIME = Array.from({ length: 61 }, (_, index) => ({
	date: new Date(Date.UTC(2026, 6, 1, index)).toISOString(),
	value: index % 5 === 0 ? 0 : 1,
}))

test('site uptime bars space evenly, dim on hover, and reset date highlights', async ({
	page,
}) => {
	await page.setViewportSize({ width: 1440, height: 900 })
	await mockAnalytics(page, UPTIME)
	await page.goto(`/dashboard/sites/${SITE_NAME}/insights/analytics`)

	const uptimeCard = page.locator('#uptime')
	const bars = uptimeCard.locator('.max-w-4')
	await expect(bars).toHaveCount(UPTIME.length, { timeout: 30000 })

	const firstBar = bars.nth(0)
	const secondBar = bars.nth(1)
	const firstBox = (await firstBar.boundingBox())!
	const secondBox = (await secondBar.boundingBox())!
	expect(secondBox.x - firstBox.x - firstBox.width).toBeCloseTo(2, 0)

	await firstBar.hover()
	await expect(secondBar).toHaveClass(/opacity-40/)
	await expect(firstBar).not.toHaveClass(/opacity-40/)

	const previousChunk = uptimeCard.getByRole('button', {
		name: 'Previous uptime chunk',
	})
	await previousChunk.click()
	const dateLabels = uptimeCard.locator('.text-ink-gray-5 > div')
	await expect(dateLabels.first()).toHaveClass(/bg-surface-gray-3/)
	await expect(dateLabels.first()).not.toHaveClass(/bg-surface-gray-3/, {
		timeout: 1000,
	})
})

test('site uptime bars stay wide enough on a phone viewport', async ({
	page,
}) => {
	await page.setViewportSize({ width: 320, height: 900 })
	await mockAnalytics(
		page,
		Array.from({ length: 120 }, (_, index) => ({
			date: new Date(Date.UTC(2026, 6, 1, index)).toISOString(),
			value: index % 5 === 0 ? 0 : 1,
		})),
	)
	await page.goto(`/dashboard/sites/${SITE_NAME}/insights/analytics`)

	const uptimeCard = page.locator('#uptime')
	const firstChunkBars = uptimeCard
		.locator('.snap-start')
		.first()
		.locator('.max-w-4')
	await expect(firstChunkBars).toHaveCount(14, { timeout: 30000 })
	await expect
		.poll(async () => (await firstChunkBars.first().boundingBox())?.width ?? 0)
		.toBeGreaterThanOrEqual(5)
})

test('resizing site uptime from its last phone chunk resets the chunk index', async ({
	page,
}) => {
	const pageErrors: Error[] = []
	page.on('pageerror', (error) => pageErrors.push(error))
	await page.setViewportSize({ width: 320, height: 900 })
	await mockAnalytics(
		page,
		Array.from({ length: 120 }, (_, index) => ({
			date: new Date(Date.UTC(2026, 6, 1, index)).toISOString(),
			value: index % 5 === 0 ? 0 : 1,
		})),
	)
	await page.goto(`/dashboard/sites/${SITE_NAME}/insights/analytics`)

	const uptimeCard = page.locator('#uptime')
	await expect(uptimeCard.locator('.max-w-4')).toHaveCount(120, {
		timeout: 30000,
	})
	const previousChunk = uptimeCard.getByRole('button', {
		name: 'Previous uptime chunk',
	})
	const nextChunk = uptimeCard.getByRole('button', {
		name: 'Next uptime chunk',
	})
	while (await nextChunk.isEnabled()) await nextChunk.click()
	await expect(previousChunk).toBeEnabled()

	await page.setViewportSize({ width: 1440, height: 900 })

	await expect(previousChunk).toBeDisabled()
	await expect(
		uptimeCard.locator('.text-ink-gray-5 > div').first(),
	).toBeVisible()
	expect(pageErrors).toEqual([])
})

test('shortening the site uptime range clamps the selected chunk', async ({
	page,
}) => {
	const pageErrors: Error[] = []
	page.on('pageerror', (error) => pageErrors.push(error))
	const shorterUptime = Array.from({ length: 50 }, (_, index) => ({
		date: new Date(Date.UTC(2027, 6, 1, index)).toISOString(),
		value: index % 5 === 0 ? 0 : 1,
	}))
	let useShorterRange = false
	await page.setViewportSize({ width: 320, height: 900 })
	await mockAnalytics(page, async () => {
		if (useShorterRange)
			await new Promise((resolve) => setTimeout(resolve, 500))
		return useShorterRange
			? shorterUptime
			: Array.from({ length: 120 }, (_, index) => ({
					date: new Date(Date.UTC(2026, 6, 1, index)).toISOString(),
					value: index % 5 === 0 ? 0 : 1,
				}))
	})
	await page.goto(`/dashboard/sites/${SITE_NAME}/insights/analytics`)

	const uptimeCard = page.locator('#uptime')
	await expect(uptimeCard.locator('.max-w-4')).toHaveCount(120, {
		timeout: 30000,
	})
	const previousChunk = uptimeCard.getByRole('button', {
		name: 'Previous uptime chunk',
	})
	const nextChunk = uptimeCard.getByRole('button', {
		name: 'Next uptime chunk',
	})
	while (await nextChunk.isEnabled()) await nextChunk.click()
	for (let index = 0; index < 6; index++) await previousChunk.click()
	await expect(nextChunk).toBeEnabled()
	await expect(uptimeCard.locator('.max-w-4')).toHaveCount(120)

	const scrollContainer = uptimeCard.locator('.overflow-x-auto.snap-x')
	const selectedDates = uptimeCard.locator('.text-ink-gray-5 > div')
	const previousFirstDate = await selectedDates.first().textContent()
	const previousScrollPosition = await scrollContainer.evaluate(
		(element) => element.scrollLeft,
	)
	expect(previousScrollPosition).toBeGreaterThan(0)

	useShorterRange = true
	await page.getByRole('combobox').last().click()
	await page.getByRole('option', { name: 'Last 6 hours' }).click()
	await expect(uptimeCard.locator('.max-w-4')).toHaveCount(0)

	await expect(uptimeCard.locator('.max-w-4')).toHaveCount(
		shorterUptime.length,
		{ timeout: 30000 },
	)
	await expect(selectedDates.first()).not.toHaveText(previousFirstDate!)
	await expect(selectedDates.first()).toContainText('2027')
	await expect
		.poll(() => scrollContainer.evaluate((element) => element.scrollLeft))
		.toBeGreaterThan(0)
	expect(pageErrors).toEqual([])
})

test('shortening uptime data from the last chunk clamps to the new last chunk', async ({
	page,
}) => {
	const pageErrors: Error[] = []
	page.on('pageerror', (error) => pageErrors.push(error))
	const shorterUptime = Array.from({ length: 20 }, (_, index) => ({
		date: new Date(Date.UTC(2027, 6, 1, index)).toISOString(),
		value: index % 5 === 0 ? 0 : 1,
	}))
	let useShorterRange = false
	await page.setViewportSize({ width: 320, height: 900 })
	await mockAnalytics(page, async () => {
		if (useShorterRange)
			await new Promise((resolve) => setTimeout(resolve, 500))
		return useShorterRange
			? shorterUptime
			: Array.from({ length: 120 }, (_, index) => ({
					date: new Date(Date.UTC(2026, 6, 1, index)).toISOString(),
					value: index % 5 === 0 ? 0 : 1,
				}))
	})
	await page.goto(`/dashboard/sites/${SITE_NAME}/insights/analytics`)

	const uptimeCard = page.locator('#uptime')
	await expect(uptimeCard.locator('.max-w-4')).toHaveCount(120, {
		timeout: 30000,
	})
	const previousChunk = uptimeCard.getByRole('button', {
		name: 'Previous uptime chunk',
	})
	const nextChunk = uptimeCard.getByRole('button', {
		name: 'Next uptime chunk',
	})
	while (await nextChunk.isEnabled()) await nextChunk.click()
	await expect(nextChunk).toBeDisabled()

	useShorterRange = true
	await page.getByRole('combobox').last().click()
	await page.getByRole('option', { name: 'Last 6 hours' }).click()
	await expect(uptimeCard.locator('.max-w-4')).toHaveCount(0)
	await expect(uptimeCard.locator('.max-w-4')).toHaveCount(
		shorterUptime.length,
		{ timeout: 30000 },
	)

	await expect(previousChunk).toBeEnabled()
	await expect(nextChunk).toBeDisabled()
	await expect(
		uptimeCard.locator('.text-ink-gray-5 > div').first(),
	).toContainText('2027')
	expect(pageErrors).toEqual([])
})
