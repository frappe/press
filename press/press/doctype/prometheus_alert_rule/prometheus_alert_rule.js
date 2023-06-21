// Copyright (c) 2021, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Prometheus Alert Rule', {
	onload_post_render: function (frm) {
		frm.trigger('resize_code_fields');
	},
	resize_code_fields: function (frm) {
		setTimeout(() => {
			frm.fields.map((field) => {
				if (field.ace_editor_target) {
					field.ace_editor_target.css('height', 100);
					field.editor.resize();
				}
			});
		}, 1000);
	},
});
