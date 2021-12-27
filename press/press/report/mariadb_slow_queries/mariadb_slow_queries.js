// Copyright (c) 2021, Frappe and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["MariaDB Slow Queries"] = {
	"filters": [
		{
			fieldname: "site",
			label: __("Site"),
			fieldtype: "Link",
			options: "Site",
			reqd: 1
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
			fieldname: "search_pattern",
			label: __("Search Pattern"),
			fieldtype: "Data",
			default: ".*",
			reqd: 1,
		},
		{
			fieldname: "format_queries",
			label: __("Format Queries"),
			fieldtype: "Check",
		},
	]
};
