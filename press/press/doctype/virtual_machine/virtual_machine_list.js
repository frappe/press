frappe.listview_settings['Virtual Machine'] = {
	onload: function (list) {
		list.page.add_menu_item(__('Sync'), function () {
			frappe.call({
				method:
					'press.press.doctype.virtual_machine.virtual_machine.sync_virtual_machines',
				callback: function () {
					listview.refresh();
				},
			});
		});
	},
};
