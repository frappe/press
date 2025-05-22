// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('MariaDB Binlog', {
	refresh(frm) {
		[[__('Download in Server'), 'download_binlog', frm.doc.uploaded]].forEach(
			([label, method, condition]) => {
				if (typeof condition === 'undefined' || condition) {
					frm.add_custom_button(label, () => {
						frappe.confirm(
							`Are you sure you want to ${label.toLowerCase()} this site?`,
							() => frm.call(method).then((r) => frm.refresh()),
						);
					});
				}
			},
		);
	},
});
