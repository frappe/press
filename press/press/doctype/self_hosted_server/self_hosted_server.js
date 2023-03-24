// Copyright (c) 2023, Frappe and contributors
// For license information, please see license.txt


frappe.ui.form.on('Self Hosted Server', {
	refresh: function (frm) {
		frm.add_web_link(
			`/dashboard/servers/${frm.doc.name}`,
			__('Visit Dashboard')
		);
		[
			[__('Create App Server'), "create_server", false],
			[__('Get Apps from Existing Bench'), "fetch_apps_and_sites", false],
			[__('Create an Release Group for Existing Bench'), "create_new_rg", false],
			[__('Create Sites from Existing Bench'), "create_new_sites", true,frm.doc.release_group],
			[__('Create Database Server'), "create_db_server", false,frm.doc.server_created],
			,
		].forEach(([label, method, confirm, condition]) => {
			if (typeof condition === "undefined" || condition) {
				frm.add_custom_button(
					label,
					() => {
						if (confirm) {
							frappe.confirm(
								`Are you sure you want to ${label.toLowerCase()}?`,
								() => frm.call(method).then((r) => {
									if (r.message) {
										frappe.msgprint(r.message);
									} else {
										frm.refresh();
									}
								})
							);

						} else {
							frm.call(method).then((r) => {
								if (r.message) {
									frappe.msgprint(r.message);
								} else {
									frm.refresh();
								}
							})
						}
					},
					__('Actions')
				);
			}
		});
	},
	onload: (frm) =>{
		frm.set_query("server",()=>{
			return {
				"filters": {
					"is_self_hosted": true,
				}
			};
		})
	},
},
);
