// Copyright (c) 2023, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Code Server', {
	refresh(frm) {
		[
			[__('Start'), 'start'],
			[__('Stop'), 'stop'],
			[__('Archive'), 'archive'],
		].forEach(([label, action, condition = true]) => {
			if (condition) {
				frm.add_custom_button(
					label,
					() => frm.call(action).then((r) => frm.refresh()),
					__('Actions'),
				);
			}
		});
	},
});
