// Copyright (c) 2016, Frappe and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Binary Log Browser"] = {
	"filters": [
		{
			fieldname: "site",
			label: __("Site"),
			fieldtype: "Link",
			options: "Site",
			reqd: 1
		},
		{
			fieldname: "file",
			label: __("Binary Log File"),
			fieldtype: "Link",
			options: "File",
			reqd: 1,
			ignore_link_validation: true,
			get_query: function () {
				let site = frappe.query_report.get_filter_value('site');
				if (site) {
					return {
						query: "press.press.report.binary_log_browser.binary_log_browser.get_files",
						filters: {'site': frappe.query_report.get_filter_value('site')}
					}
				}
			}
		},
		{
			fieldname: "start_datetime",
			label: __("Start From"),
			fieldtype: "Datetime",
			reqd: 1,
		},
		{
			fieldname: "stop_datetime",
			label: __("End At"),
			fieldtype: "Datetime",
			reqd: 1,
		},
		{
			fieldname: "pattern",
			label: __("Search Pattern"),
			fieldtype: "Data",
			default: ".*",
			reqd: 1,
		},
		{
			fieldname: "max_lines",
			label: __("Max Lines"),
			fieldtype: "Int",
			default: 4000,
		},
		{
			fieldname: "format_queries",
			label: __("Format Queries"),
			fieldtype: "Check",
		},
	],
};


