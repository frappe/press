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
			(column.fieldname.startsWith('disk_') && data[column.fieldname] >= 85) ||
			(column.fieldname === 'disk' &&
				(data.disk || '')
					.match(/[\d.]+(?=%)/g)
					?.some((p) => parseFloat(p) >= 85))
		if (bad) {
			value = `<span style="color: var(--red-600); font-weight: 600">${value}</span>`
		}
		return value
	},
	// Frappe draws one chart. The report sends the rest in chart.charts.
	after_datatable_render() {
		let report = frappe.query_report
		report.page.main.find('.build-server-charts').remove()
		let charts = report.raw_data?.chart?.charts || []
		let $grid = $('<div class="build-server-charts">')
			.css({
				display: 'grid',
				gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 480px), 1fr))',
				gap: 'var(--margin-md)',
				marginTop: 'var(--margin-lg)',
			})
			.appendTo(report.$chart)
		for (let options of charts) {
			let $card = $('<div>').appendTo($grid)
			$('<h6 class="text-muted">').text(options.name).appendTo($card)
			let wrapper = $('<div>').appendTo($card)[0]
			if (!options.data.labels.length) {
				$(wrapper).addClass('text-muted small').text('Nothing in this period')
				continue
			}
			new frappe.Chart(wrapper, { ...options, height: 240 })
		}
	},
}
