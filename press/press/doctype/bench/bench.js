// Copyright (c) 2019, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bench', {
	onload: function (frm) {
		frm.set_query("candidate", function () {
			return {
				"filters": {
					"group": frm.doc.group,
				}
			};
		});
	},

	refresh: function (frm) {
		[
			[__('Archive'), 'archive'],
			[__('Sync Sites Info'), 'sync_info'],
			[__('Update All Sites'), 'update_all_sites'],
			[__('Remove SSH User from Proxy'), 'remove_ssh_user', frm.doc.is_ssh_proxy_setup],
			[__('Add SSH User to Proxy'), 'add_ssh_user', !frm.doc.is_ssh_proxy_setup],
		].forEach(([label, method, condition]) => {
			if (typeof condition === "undefined" || condition){	
				frm.add_custom_button(
					label,
					() => {
						frappe.confirm(
							`Are you sure you want to ${label.toLowerCase()} this bench?`,
							() => frm.call(method).then((r) => frm.refresh())
						);
					},
					__('Actions')
				);
			}
		});
	}
});
