import { describe, expect, it, vi } from 'vitest'

vi.mock('@/data/ui', () => ({ searchModalOpen: { value: false } }))
vi.mock('./integrations', () => ({ addIntegrations: () => {} }))

import { filterLabels, highlightMatch } from './utils'

describe('highlightMatch', () => {
	it('returns the text unchanged when the query is empty', () => {
		expect(highlightMatch('my-site.frappe.cloud', '')).toBe(
			'my-site.frappe.cloud',
		)
	})

	it('wraps every case-insensitive occurrence in a mark tag', () => {
		expect(highlightMatch('Site One, site two', 'site')).toBe(
			'<mark>Site</mark> One, <mark>site</mark> two',
		)
	})

	it('escapes regex special characters in the query instead of treating them as a pattern', () => {
		expect(highlightMatch('cost: $5.00', '$5.00')).toBe(
			'cost: <mark>$5.00</mark>',
		)
	})

	it('does not throw on an unbalanced regex character in the query', () => {
		expect(() => highlightMatch('a(b', '(')).not.toThrow()
		expect(highlightMatch('a(b', '(')).toBe('a<mark>(</mark>b')
	})
})

describe('filterLabels', () => {
	const data = {
		Sites: {
			items: [{ name: 'my-site.frappe.cloud' }, { name: 'blog.example.com' }],
		},
		Servers: { items: [{ name: 'f1.frappe.cloud' }] },
	}

	it('keeps a whole group when the group name matches the query', () => {
		const result = filterLabels(data, 'Server')
		expect(Object.keys(result)).toEqual(['Servers'])
		expect(result.Servers.items).toHaveLength(1)
	})

	it('filters items within a group by name when the group itself does not match', () => {
		const result = filterLabels(data, 'blog')
		expect(Object.keys(result)).toEqual(['Sites'])
		expect(result.Sites.items).toEqual([{ name: 'blog.example.com' }])
	})

	it('matches case-insensitively', () => {
		const result = filterLabels(data, 'MY-SITE')
		expect(result.Sites.items).toEqual([{ name: 'my-site.frappe.cloud' }])
	})

	it('drops groups with no matching items and no matching group name', () => {
		const result = filterLabels(data, 'nothing-matches-this')
		expect(result).toEqual({})
	})
})
