export default {
	doctype: 'Site',
	list: {
		route: '/sites',
		title: 'Sites',
		columns: [
			{ label: 'Site', fieldname: 'name', type: 'Data' },
			{ label: 'Status', fieldname: 'status', type: 'Badge' },
			{ label: 'Cluster', fieldname: 'cluster', type: 'Data' },
			{ label: 'Bench', fieldname: 'group', type: 'Data' },
			{ label: 'Plan', fieldname: 'plan', type: 'Data' }
		]
	},
	detail: {
		titleField: 'name',
		route: '/sites/:name',
		tabs: [
			{
				label: 'Overview',
				route: ''
			},
			{
				label: 'Apps',
				route: 'apps',
				type: 'list',
				list: {
					url: 'press.api.site.installed_apps',
					doctype: 'Site App',
					filters: site => {
						return { site: site.doc.name };
					},
					columns: [
						{
							label: 'App',
							fieldname: 'app',
							width: '12rem'
						},
						{
							label: 'Branch',
							fieldname: 'branch',
							type: 'Badge',
							width: '12rem'
						},
						{
							label: 'Commit',
							fieldname: 'hash',
							type: 'Badge',
							width: '12rem',
							format(value) {
								return value.slice(0, 7);
							}
						},
						{
							label: 'Commit Message',
							fieldname: 'commit_message',
							width: 2
						}
					]
				}
			},
			{
				label: 'Domains',
				route: 'domains',
				type: 'list',
				list: {
					doctype: 'Site Domain',
					filters: site => {
						return { site: site.doc.name };
					},
					columns: [
						{
							label: 'Domain',
							fieldname: 'domain'
						},
						{
							label: 'Status',
							fieldname: 'status',
							type: 'Badge'
						},
						{
							label: 'Primary',
							fieldname: 'primary',
							type: 'Icon',
							Icon(value) {
								return value ? 'check' : '';
							}
						},
						{
							label: 'DNS Type',
							fieldname: 'dns_type',
							type: 'Badge'
						}
					]
				}
			},
			{
				label: 'Backups',
				route: 'backups',
				type: 'list',
				list: {
					doctype: 'Site Backup',
					filters: site => {
						return {
							site: site.doc.name,
							status: ['in', ['Pending', 'Running', 'Success']]
						};
					},
					columns: [
						{
							label: 'Timestamp',
							fieldname: 'creation',
							format(value) {
								let timestamp = new Date(value);
								return `Backup on ${timestamp.toLocaleDateString()} at ${timestamp.toLocaleTimeString()}`;
							}
						},
						{
							label: 'Backup with files',
							fieldname: 'with_files',
							type: 'Icon',
							Icon(value) {
								return value ? 'check' : '';
							}
						},
						{
							label: 'Offsite Backup',
							fieldname: 'offsite',
							type: 'Icon',
							Icon(value) {
								return value ? 'check' : '';
							}
						}
					]
				}
			},
			{
				label: 'Activity',
				route: 'activity',
				type: 'list',
				list: {
					doctype: 'Site Activity',
					filters: site => {
						return { site: site.doc.name };
					},
					fields: ['owner'],
					orderBy: 'creation desc',
					columns: [
						{
							label: 'Action',
							fieldname: 'action',
							format(value, row) {
								let action = row.action;
								if (action == 'Create') {
									action = 'Site created';
								}
								return `${action} by ${row.owner}`;
							}
						},
						{
							label: 'Reason',
							fieldname: 'reason'
						},
						{
							label: 'Timestamp',
							fieldname: 'creation'
						}
					]
				}
			},
			{
				label: 'Settings',
				route: 'settings'
			}
		]
	}
};
