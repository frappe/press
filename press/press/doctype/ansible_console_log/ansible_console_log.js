// Copyright (c) 2023, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Ansible Console Log', {
	refresh(frm) {
		frm.add_custom_button(__('Re-Run in Console'), () => {
			window.localStorage.setItem(
				'ansible_console_inventory',
				frm.doc.inventory,
			);
			window.localStorage.setItem('ansible_console_command', frm.doc.command);
			frappe.set_route('Form', 'Ansible Console');
		});
	},
});
