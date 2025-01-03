// Copyright (c) 2024, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Devbox', {
	setup: function (frm) {
		frm.set_query('server', function () {
			// Replace your_link_field with the actual field name
			return {
				filters: [
					['Server', 'is_devbox_server', '=', true], // Replace YourLinkedDocType with the linked DocType
				],
			};
		});
	},
	refresh(frm) {
		if (!frm.doc.initialized && frm.doc.status == 'Pending') {
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

		if (!(frm.doc.status == 'Destroyed')) {
			if (!(frm.doc.status == 'Exited') || !(frm.doc.status == 'Pending')) {
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

			frm.add_custom_button(
				__('Sync Docker Volumes Size'),
				() => {
					frm.call('sync_devbox_docker_volumes_size');
				},
				__('Actions'),
			);
		}

		if (['Starting', 'Running'].includes(frm.doc.status)) {
			frm.add_custom_button(
				__('Go to Devbox'),
				() => {
					window.open(`https://${frm.doc.name}/vnc.html`, '_blank');
				},
				__('Actions'),
			);
		}
		frm.add_custom_button(
			__('Destroy Devbox'),
			() => {
				frm.call('destroy_devbox');
			},
			__('Actions'),
		);
	},
});
