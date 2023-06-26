// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.listview_settings['Invoice'] = {
	get_indicator: function (doc) {
		var status_color = {
			Draft: 'darkgrey',
			Unpaid: 'orange',
			Paid: 'green',
			'Invoice Created': 'blue',
		};
		return [__(doc.status), status_color[doc.status], 'status,=,' + doc.status];
	},
};
