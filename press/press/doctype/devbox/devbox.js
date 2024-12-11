// Copyright (c) 2024, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Devbox', {
	refresh(frm) {
		frm.add_custom_button(
			__('Get Available CPU and RAM'),
			() => {
				frm.call('get_available_cpu_and_ram');
			},
			__('Information'),
		);

		if (!frm.doc.initialized) {
			frm.add_custom_button(
				__('Initialize'),
				() => {
					frm.call('initialize_devbox');
				},
				__('Actions'),
			);
		}

		if (frm.doc.status == 'Exited') {
			frm.add_custom_button(
				__('Start'),
				() => {
					frm.call('start_devbox');
				},
				__('Actions'),
			);
		}

		if (!(frm.doc.status == 'Exited')) {
			frm.add_custom_button(
				__('Stop'),
				() => {
					frm.call('stop_devbox');
				},
				__('Actions'),
			);
		}

		frm.add_custom_button(
			__('Sync Status'),
			() => {
				frm.call('sync_devbox_status');
			},
			__('Actions'),
		);

		if (['Starting', 'Running'].includes(frm.doc.status)) {
			frm.add_custom_button(
				__('Go to Devbox'),
				() => {
					window.open(`https://${frm.doc.name}/vnc.html`, '_blank');
				},
				__('Actions'),
			);
		}
	},
});
