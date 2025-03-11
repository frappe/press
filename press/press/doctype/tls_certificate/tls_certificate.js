// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('TLS Certificate', {
	refresh: function (frm) {
		if (frm.doc.wildcard) {
			frm.add_custom_button(__('Trigger Callback'), () => {
				frm.call({
					method: 'trigger_server_tls_setup_callback',
					doc: frm.doc,
					callback: (result) => frm.refresh(),
				});
			});
		}

		frm.trigger('show_obtain_certificate');
		frm.trigger('toggle_read_only');
		frm.trigger('toggle_hidden');
		frm.trigger('toggle_copy_private_key');
	},

	custom: function (frm) {
		frm.trigger('show_obtain_certificate');
		frm.trigger('toggle_read_only');
		frm.trigger('toggle_hidden');
		frm.trigger('toggle_copy_private_key');
	},

	toggle_copy_private_key: function (frm) {
		if (!frm.doc.wildcard) {
			frm.add_custom_button('Copy Private Key', () => {
				frappe.confirm(
					`Are you sure you want to copy private
					key. You should ONLY do this for custom
					domains. And notify user of their
					responsibility on handling private
					key.`,
					() => frappe.utils.copy_to_clipboard(frm.doc.private_key),
				);
			});
		}

		if (frm.doc.custom) {
			frm.remove_custom_button('Copy Private Key');
		}
	},

	show_obtain_certificate: function (frm) {
		if (!frm.doc.custom) {
			frm.add_custom_button(__('Obtain Certificate'), () => {
				frm.call({
					method: 'obtain_certificate',
					doc: frm.doc,
					callback: (result) => frm.refresh(),
				});
			});
		}
	},

	toggle_read_only: function (frm) {
		let fields = [
			'certificate',
			'private_key',
			'intermediate_chain',
			'full_chain',
			'issued_on',
			'expires_on',
		];
		fields.forEach(function (field) {
			frm.set_df_property(field, 'read_only', !frm.doc.custom);
			frm.refresh_field(field);
		});
	},

	toggle_hidden: function (frm) {
		frm.set_df_property('private_key', 'hidden', !frm.doc.custom);
		frm.refresh_field('private_key');
	},
});
