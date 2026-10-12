import { expect, test } from './coverage.fixture'
import { mockAnalytics, SITE_NAME } from './analytics-fixture'

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

	const previousChunk = uptimeCard.locator('button').first()
	await previousChunk.click()
	const dateLabels = uptimeCard.locator('.transition-colors')
	await expect(dateLabels.first()).toHaveClass(/bg-surface-gray-3/)
	await expect(dateLabels.first()).not.toHaveClass(/bg-surface-gray-3/, {
		timeout: 1000,
	})
})
