// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.listview_settings['Cloud Usage Anomaly'] = {
	// Growth a driver explained is kept for the record, not for the queue.
	filters: [['verdict', '=', 'Inorganic']],

	get_indicator(doc) {
		const colours = {
			Open: 'red',
			Acknowledged: 'orange',
			Resolved: 'green',
			'False Positive': 'gray',
		}
		return [
			__(doc.status),
			colours[doc.status] || 'gray',
			`status,=,${doc.status}`,
		]
	},
}
