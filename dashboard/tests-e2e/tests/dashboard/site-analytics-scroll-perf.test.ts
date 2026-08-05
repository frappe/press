import type { Page } from '@playwright/test'
import {
	mockAnalytics,
	RANGE_END,
	RANGE_START,
	SITE_NAME,
} from './analytics-fixture'
import { expect, test } from './coverage.fixture'

type ScrollStats = {
	frames: number
	longFrames: number
	worstFrameMs: number
	longTaskMs: number
	chartNodes: number
	canvases: number
}

/**
 * Drive the page's scroller from a rAF loop and record how many frames blew
 * past the 32ms (30fps) budget. rAF-driven rather than mouse.wheel so the
 * measurement is deterministic and independent of scroll physics.
 */
async function measureScroll(page: Page): Promise<ScrollStats> {
	return page.evaluate(async () => {
		const scroller =
			[...document.querySelectorAll<HTMLElement>('*')].find(
				(el) =>
					el.scrollHeight > el.clientHeight + 200 &&
					['auto', 'scroll'].includes(getComputedStyle(el).overflowY),
			) ?? document.scrollingElement!

		const deltas: number[] = []
		let longTaskMs = 0
		const observer = new PerformanceObserver((list) => {
			for (const entry of list.getEntries()) longTaskMs += entry.duration
		})
		observer.observe({ entryTypes: ['longtask'] })

		await new Promise<void>((resolve) => {
			const started = performance.now()
			let previous = started
			let direction = 1
			const step = (now: number) => {
				deltas.push(now - previous)
				previous = now

				scroller.scrollTop += direction * 45
				const atBottom =
					scroller.scrollTop + scroller.clientHeight >=
					scroller.scrollHeight - 2
				if (atBottom) direction = -1
				if (scroller.scrollTop <= 0) direction = 1

				if (now - started > 4000) return resolve()
				requestAnimationFrame(step)
			}
			requestAnimationFrame(step)
		})
		observer.disconnect()

		// Drop the first frame: it carries the gap since the previous paint.
		const frames = deltas.slice(1)
		return {
			frames: frames.length,
			longFrames: frames.filter((d) => d > 32).length,
			worstFrameMs: Math.round(Math.max(...frames)),
			longTaskMs: Math.round(longTaskMs),
			chartNodes: document.querySelectorAll('.chart svg *').length,
			canvases: document.querySelectorAll('.chart canvas').length,
		}
	})
}

/** Open the tab with a 15-day range and wait for every chart to be painted. */
async function openAdvancedAnalytics(page: Page) {
	await page.setViewportSize({ width: 1440, height: 900 })
	await mockAnalytics(page)

	const query = `?start=${RANGE_START.toISOString()}&end=${RANGE_END.toISOString()}`
	await page.goto(`/dashboard/sites/${SITE_NAME}/insights/analytics${query}`)

	await page.getByText('Advanced Analytics').click()

	// 14 advanced bar charts plus 5 base line charts must be painted before
	// measuring, otherwise we time an empty page.
	await expect
		.poll(() => page.locator('.chart').count(), { timeout: 30000 })
		.toBeGreaterThanOrEqual(19)
	await page.waitForTimeout(5000)
}

test('advanced analytics leaves the main thread idle once charts are painted', async ({
	page,
}) => {
	test.slow()
	await openAdvancedAnalytics(page)

	// Guards the echarts feedback loop: a `finished` handler that dispatches an
	// action re-triggers `finished`, so the charts re-render forever and the tab
	// burns a core for as long as it is open. Scroll jank is the symptom users
	// report, but the page is just as busy sitting still.
	const idleLongTaskMs = await page.evaluate(async () => {
		let longTaskMs = 0
		const observer = new PerformanceObserver((list) => {
			for (const entry of list.getEntries()) longTaskMs += entry.duration
		})
		observer.observe({ entryTypes: ['longtask'] })
		await new Promise((resolve) => setTimeout(resolve, 3000))
		observer.disconnect()
		return Math.round(longTaskMs)
	})

	expect(
		idleLongTaskMs,
		'main-thread work over 3s of doing nothing',
	).toBeLessThan(250)
})

test('advanced analytics scrolls smoothly with a full 15-day dataset', async ({
	page,
}) => {
	test.slow()
	await openAdvancedAnalytics(page)

	const stats = await measureScroll(page)
	console.log('scroll stats:', JSON.stringify(stats))

	// Jitter shows up as frames that miss the 30fps budget, and as long tasks
	// hogging the main thread for most of the scroll.
	const fps = stats.frames / 4
	expect(fps, 'frames per second while scrolling').toBeGreaterThan(30)
	expect(
		stats.longFrames / stats.frames,
		'share of frames over the 32ms budget',
	).toBeLessThan(0.15)
	expect(
		stats.longTaskMs,
		'main-thread long tasks over a 4s scroll',
	).toBeLessThan(1000)
})
