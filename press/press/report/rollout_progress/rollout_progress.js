// Copyright (c) 2026, Frappe and contributors
// For license information, please see license.txt

frappe.query_reports['Rollout Progress'] = {
	filters: [
		{
			fieldname: 'deploy_candidate',
			label: __('Deploy Candidate'),
			fieldtype: 'Link',
			options: 'Deploy Candidate',
			reqd: 1,
		},
	],
}
