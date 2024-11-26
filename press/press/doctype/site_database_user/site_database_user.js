// Copyright (c) 2024, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Site Database User', {
	refresh(frm) {
		[
			[__('Apply Changes'), 'apply_changes', true],
			[
				__('Create User in Database'),
				'create_user',
				!frm.doc.user_created_in_database,
			],
			[
				__('Remove User from Database'),
				'remove_user',
				frm.doc.user_created_in_database,
			],
			[
				__('Add User to ProxySQL'),
				'add_user_to_proxysql',
				!frm.doc.user_added_in_proxysql,
			],
			[
				__('Remove User from ProxySQL'),
				'remove_user_from_proxysql',
				frm.doc.user_added_in_proxysql,
			],
			[__('Archive User'), 'archive', frm.doc.status !== 'Archived'],
		].forEach(([label, method, condition]) => {
			if (typeof condition === 'undefined' || condition) {
				frm.add_custom_button(
					label,
					() => {
						frappe.confirm(
							`Are you sure you want to ${label.toLowerCase()} this site?`,
							() => frm.call(method).then((r) => frm.refresh()),
						);
					},
					__('Actions'),
				);
			}
		});

		frm.add_custom_button(
			__('Show Credential'),
			() =>
				frm.call('get_credential').then((r) => {
					let message = `Host: ${r.message.host}

Port: ${r.message.port}

Database: ${r.message.database}

Username: ${r.message.username}

Password: ${r.message.password}

\`\`\`\nmysql -u ${r.message.username} -p${r.message.password} -h ${r.message.host} -P ${r.message.port} --ssl --ssl-verify-server-cert\n\`\`\``;

					frappe.msgprint(frappe.markdown(message), 'Database Credentials');
				}),
			__('Actions'),
		);
	},
});
