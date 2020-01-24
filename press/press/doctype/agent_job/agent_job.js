// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Agent Job', {
	refresh: function(frm) {
		frm.add_custom_button(__('Steps'), () => {
			const filters = {agent_job: frm.doc.name};
			frappe.set_route("List", "Agent Job Step", filters);
		});
	}
});
