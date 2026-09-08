// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports['Build Server Stats'] = {
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data)
		if (!data) return value
		let bad =
			(column.fieldname === 'iowait' && data.iowait >= 20) ||
			(column.fieldname === 'retransmit' && data.retransmit >= 1) ||
			(column.fieldname === 'drops' && data.drops > 0) ||
			(column.fieldname === 'disk' &&
				(data.disk || '')
					.match(/[\d.]+(?=%)/g)
					?.some((p) => parseFloat(p) >= 85))
		if (bad) {
			value = `<span style="color: var(--red-600); font-weight: 600">${value}</span>`
		}
		return value
	},
}
