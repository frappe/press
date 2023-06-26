// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('App Release', {
	refresh: function (frm) {
		[
			[__("Clone"), "clone", true, !frm.doc.cloned],
			[__("Cleanup"), "cleanup", true, frm.doc.cloned],
		].forEach(([label, method, confirm, condition]) => {
			if (typeof condition === 'undefined' || condition) {
				frm.add_custom_button(
					label,
					() => {
						if (confirm) {
							frappe.confirm(
								`Are you sure you want to ${label.toLowerCase()}?`,
								() =>
									frm.call(method).then((r) => {
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
							});
						}
					},
					__('Actions')
				);
			}
		});
		frm.add_custom_button(
			__('View'),
			() => {
				window.open(frm.doc.code_server_url);
			},
		);
	},
});
