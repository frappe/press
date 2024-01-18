// Copyright (c) 2023, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Ansible Console', {
	onload: function (frm) {
		frappe.ui.keys.add_shortcut({
			shortcut: 'shift+enter',
			action: () => frm.page.btn_primary.trigger('click'),
			page: frm.page,
			description: __('Execute Ansible Command'),
			ignore_inputs: true,
		});
	},
	refresh: function (frm) {
		frm.fields_dict.output.grid.grid_pagination.page_length = 500;
		frm.disable_save();
		frm.page.set_primary_action(__('Execute'), ($btn) => {
			frm.set_value('nonce', Math.random());
			frm.clear_table('output');
			$btn.text(__('Executing...'));
			return frm
				.execute_action('Execute')
				.finally(() => $btn.text(__('Execute')));
		});

		if (window.localStorage.getItem('ansible_console_command')) {
			frm.set_value(
				'inventory',
				window.localStorage.getItem('ansible_console_inventory'),
			);
			frm.set_value(
				'command',
				window.localStorage.getItem('ansible_console_command'),
			);

			window.localStorage.removeItem('ansible_console_inventory');
			window.localStorage.removeItem('ansible_console_command');
		}

		frappe.realtime.off('ansible_console_update');
		frappe.realtime.on('ansible_console_update', (message) => {
			if (message.nonce == frm.doc.nonce) {
				frm.set_value('output', message.output);
			}
		});
	},
});
