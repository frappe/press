// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt


frappe.provide("frappe.press.DataTable");

class DataTable {
	constructor({
		frm,
		table_field,
		data_field,
		columns,
	}) {
		this.wrapper = frm.get_field(table_field).$wrapper;
		frm.set_df_property(data_field, "hidden", 1);
		this.data = JSON.parse(frm.doc[data_field]);
		this.columns = columns;
	}

	refresh() {
		this.make_wrapper();
		this.render_datatable();
	}

	make_wrapper() {
		this.wrapper.empty();
		this.wrapper.html(`
		<div>
			<div class="row">
				<div class="col-sm-12">
					<div class="table border"></div>
				</div>
			</div>
		</div>
	`);
	}

	render_datatable() {
		frappe.require('/assets/js/press-datatable.js', () => {
			this.$table = this.wrapper.find('.table');
			this.datatable = new frappe.press.DataTable(this.$table.get(0), {
				data: this.data,
				columns: this.columns,
				layout: this.columns.length < 15 ? 'fluid' : 'fixed',
				cellHeight: 35,
				serialNoColumn: false,
				checkboxColumn: false,
				noDataMessage: __('No Data'),
				disableReorderColumn: true
			});
		});

	}
}



frappe.ui.form.on('Server Status', {
	refresh: function(frm) {

		let mariadb_process_list_table = new DataTable({
			frm: frm,
			table_field: "mariadb_process_list_table",
			data_field: "mariadb_process_list",
			columns: ["Id", "User", "Host", "db", "Command", "Time", "State", "Info"],
		});
		mariadb_process_list_table.refresh();

		let supervisor_status_table = new DataTable({
			frm: frm,
			table_field: "supervisor_status_table",
			data_field: "supervisor_status",
			columns: ["name", "group", "online", "state", "description"],
		});
		supervisor_status_table.refresh();

		let process_list_table = new DataTable({
			frm: frm,
			table_field: "process_list_table",
			data_field: "process_list",
			columns: ["USER", "PID", "%CPU", "%MEM", "VSZ", "RSS", "TTY", "STAT", "START", "TIME", "COMMAND"],
		});
		process_list_table.refresh();
	}
});
