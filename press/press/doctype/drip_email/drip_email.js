// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Drip Email', {
	refresh: function (frm) {
		const doc = frm.doc;
		const can_write = frappe.boot.user.can_write.includes(doc.doctype);
		if (!frm.is_new() && !frm.is_dirty() && !doc.email_sent && can_write) {
			frm.add_custom_button('Send a test email', () => {
				frm.events.send_test_email(frm);
			});
		}
	},

	send_test_email(frm) {
		let d = new frappe.ui.Dialog({
			title: __('Send Test Email'),
			fields: [
				{
					label: __('Site'),
					fieldname: 'site',
					fieldtype: 'Link',
					options: 'Site',
				},
				{
					label: __('Email'),
					fieldname: 'email',
					fieldtype: 'Data',
					options: 'Email',
				},
			],
			primary_action_label: __('Send'),
			primary_action({ site, email }) {
				d.get_primary_btn().text(__('Sending...')).prop('disabled', true);
				frm.call('send_test_email', { site, email }).then(() => {
					d.get_primary_btn().text(__('Send again')).prop('disabled', false);
				});
			},
		});
		d.show();
	},
});
