// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Cloud Cost Settings', {
	refresh(frm) {
		frm.add_custom_button(__('Backfill Cost History'), () => {
			frappe.confirm(
				__(
					'Cost Explorer charges $0.01 per request. This reads {0} months, one request per month.',
					[frm.doc.backfill_months || 14],
				),
				() =>
					frm
						.call('backfill_cost_history')
						.then((r) => frappe.msgprint(r.message)),
			)
		})

		frm.add_custom_button(__('Backfill Driver History'), () =>
			frm
				.call('backfill_driver_history')
				.then((r) => frappe.msgprint(r.message)),
		)

		frm.add_custom_button(__('Cloud Cost Drilldown'), () =>
			frappe.set_route('query-report', 'Cloud Cost Drilldown'),
		)
	},
})
