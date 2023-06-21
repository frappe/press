// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Press Settings', {
	create_stripe_webhook(frm) {
		frm.call('create_stripe_webhook');
	},
	create_github_app(frm) {
		frm.call({
			method: 'get_github_app_manifest',
			doc: frm.doc,
			callback: (response) => {
				window.location.href = response.message;
				let $form = $('<form>', {
					action: 'https://github.com/settings/apps/new',
					method: 'post',
				});
				$('<input>')
					.attr({
						type: 'hidden',
						name: 'manifest',
						value: JSON.stringify(response.message),
					})
					.appendTo($form);
				$form.appendTo('body').submit();
			},
		});
	},
});
