import dayjs from '../utils/dayjs';
import { formatDuration } from '../utils/format';

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
	},
	detail: {
		titleField: 'title',
		route: '/benches/:name',
		tabs: [
			{
				label: 'Deploys',
				route: 'deploys',
				type: 'list',
				list: {
					doctype: 'Deploy Candidate',
					route: row => ({ name: 'Bench Deploy', params: { id: row.name } }),
					filters: group => {
						return {
							group: group.name
						};
					},
					orderBy: 'creation desc',
					fields: [{ apps: ['app'] }],
					columns: [
						{
							label: 'Deploy',
							fieldname: 'creation',
							format(value) {
								return `Deploy on ${dayjs(value).toLocaleString()}`;
							},
							width: 2
						},
						{
							label: 'Status',
							fieldname: 'status',
							type: 'Badge'
						},

						{
							label: 'Apps',
							fieldname: 'apps',
							format(value, row) {
								return (row.apps || []).map(d => d.app).join(', ');
							}
						},
						{
							label: 'Duration',
							fieldname: 'build_duration',
							format: formatDuration,
							class: 'text-gray-600'
						}
					]
				}
			}
		]
	},
	routes: [
		{
			name: 'Bench Deploy',
			path: 'deploy/:id',
			component: () => import('../pages/BenchDeploy.vue')
		}
	]
};
