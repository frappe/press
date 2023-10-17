export default {
	doctype: 'Release Group',
	list: {
		route: '/benches',
		title: 'Benches',
		columns: [
			{ label: 'Title', fieldname: 'title', fieldtype: 'Data' },
			{ label: 'Version', fieldname: 'version', fieldtype: 'Data' },
			{
				label: 'Auto Deploy',
				fieldname: 'is_push_to_deploy_enabled',
				fieldtype: 'Check',
				format(value) {
					return value ? 'Yes' : 'No';
				}
			}
		]
	}
};
