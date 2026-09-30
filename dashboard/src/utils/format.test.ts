import { describe, expect, it, vi } from 'vitest'

vi.mock('../data/team', () => ({ getTeam: () => ({ doc: {} }) }))
vi.mock('frappe-ui', () => ({ getConfig: () => undefined }))

import {
	bytes,
	commaAnd,
	commaSeparator,
	escapeHtml,
	formatCommaSeperatedNumber,
	formatMilliseconds,
	formatSeconds,
	numberK,
	plural,
	secsToDuration,
} from './format'

describe('bytes', () => {
	it('formats zero as 0 Bytes', () => {
		expect(bytes(0)).toBe('0 Bytes')
	})

	it('picks the right unit for the magnitude', () => {
		expect(bytes(1024)).toBe('1 KB')
		expect(bytes(1024 * 1024)).toBe('1 MB')
	})

	it('shifts the unit window when current is set', () => {
		expect(bytes(1024, 2, 1)).toBe('1 MB')
	})
})

describe('escapeHtml', () => {
	it('escapes all five reserved characters', () => {
		expect(escapeHtml(`<a href="x">it's & me</a>`)).toBe(
			'&lt;a href=&quot;x&quot;&gt;it&#39;s &amp; me&lt;/a&gt;',
		)
	})

	it('treats null and undefined as empty string', () => {
		expect(escapeHtml(null)).toBe('')
		expect(escapeHtml(undefined)).toBe('')
	})
})

describe('secsToDuration', () => {
	it('returns empty string for 0 and null', () => {
		expect(secsToDuration(0)).toBe('0s')
		expect(secsToDuration(null)).toBe('')
	})

	it('combines hours, minutes and seconds', () => {
		expect(secsToDuration(3725)).toBe('1h 2m 5s')
	})

	it('drops zero-valued units', () => {
		expect(secsToDuration(3600)).toBe('1h')
	})
})

describe('plural', () => {
	it('picks singular for exactly one, parsing string input', () => {
		expect(plural('1', 'site', 'sites')).toBe('site')
		expect(plural(1, 'site', 'sites')).toBe('site')
	})

	it('picks plural for anything else', () => {
		expect(plural(0, 'site', 'sites')).toBe('sites')
		expect(plural(2, 'site', 'sites')).toBe('sites')
	})
})

describe('numberK', () => {
	it('leaves numbers under 1000 unchanged', () => {
		expect(numberK(999)).toBe(999)
	})

	it('formats round thousands without a decimal', () => {
		expect(numberK(8000)).toBe('8k')
	})

	it('rounds values just under a thousand boundary up', () => {
		expect(numberK(8999)).toBe('9k')
	})
})

describe('commaSeparator and commaAnd', () => {
	it('joins two items with the given word', () => {
		expect(commaSeparator(['a', 'b'], 'or')).toBe('a or b')
	})

	it('joins three or more items with commas and the word before the last', () => {
		expect(commaSeparator(['a', 'b', 'c'], 'or')).toBe('a, b or c')
	})

	it('returns the single item unchanged', () => {
		expect(commaSeparator(['a'], 'or')).toBe('a')
	})

	it('commaAnd uses "and" as the joining word', () => {
		expect(commaAnd(['a', 'b'])).toBe('a and b')
	})
})

describe('formatSeconds', () => {
	it('shows 0s for zero', () => {
		expect(formatSeconds(0)).toBe('0s')
	})

	it('shows bare seconds for durations of a minute or less', () => {
		expect(formatSeconds(45)).toBe('45s')
	})

	it('combines hours, minutes and seconds above a minute', () => {
		expect(formatSeconds(3725)).toBe('1h 2m 5s')
	})
})

describe('formatCommaSeperatedNumber', () => {
	it('groups using the Indian lakh/crore convention', () => {
		expect(formatCommaSeperatedNumber(100000)).toBe('1,00,000')
		expect(formatCommaSeperatedNumber(1234567)).toBe('12,34,567')
	})

	it('leaves numbers under a thousand unchanged', () => {
		expect(formatCommaSeperatedNumber(500)).toBe('500')
	})
})

describe('formatMilliseconds', () => {
	it('keeps millisecond precision under 100ms and trims trailing zeros', () => {
		expect(formatMilliseconds(99)).toBe('99ms')
		expect(formatMilliseconds(12.5)).toBe('12.5ms')
	})

	it('switches to seconds between 100ms and a minute', () => {
		expect(formatMilliseconds(1500)).toBe('1.5s')
	})

	it('switches to minutes at a minute and above', () => {
		expect(formatMilliseconds(90000)).toBe('1.5m')
	})
})
