// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Deploy Candidate', {
	refresh: function (frm) {
		frm.fields_dict['apps'].grid.get_field('app').get_query = function (doc) {
			return {
				"query": "press.press.doctype.deploy_candidate.deploy_candidate.desk_app",
				"filters": { 'release_group': doc.group }
			}
		}
	}
});
