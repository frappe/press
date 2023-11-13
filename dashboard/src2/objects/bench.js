import dayjs from '../utils/dayjs';
import { duration } from '../utils/format';
import { icon } from '../utils/components';

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
							width: '25rem'
						},
						{
							label: 'Status',
							fieldname: 'status',
							type: 'Badge',
							width: 0.5
						},
						{
							label: 'Apps',
							fieldname: 'apps',
							format(value, row) {
								return (row.apps || []).map(d => d.app).join(', ');
							},
							width: '20rem'
						},
						{
							label: 'Duration',
							fieldname: 'build_duration',
							format: duration,
							class: 'text-gray-600',
							width: 1
						}
					]
				}
			},
			{
				label: 'Jobs',
				icon: icon('truck'),
				// highlight: route =>
				// 	['Site Detail Jobs', 'Site Job'].includes(route.name),
				route: 'jobs',
				type: 'list',
				list: {
					doctype: 'Agent Job',
					userFilters: {},
					filters: group => {
						return { group: group.doc.name };
					},
					route(row) {
						return {
							name: 'Bench Job',
							params: { id: row.name }
						};
					},
					orderBy: 'creation desc',
					columns: [
						{
							label: 'Job Type',
							fieldname: 'job_type'
						},
						{
							label: 'Status',
							fieldname: 'status',
							type: 'Badge',
							width: '7rem'
						},
						{
							label: 'Site',
							fieldname: 'site',
							class: 'text-gray-600'
						},
						{
							label: 'Job ID',
							fieldname: 'job_id',
							class: 'text-gray-600',
							width: '7rem'
						},
						{
							label: 'Duration',
							fieldname: 'duration',
							class: 'text-gray-600',
							format: duration,
							width: '7rem'
						},
						{
							label: 'Start Time',
							fieldname: 'start',
							class: 'text-gray-600',
							format(value) {
								if (!value) return;
								return dayjs(value).format('DD/MM/YYYY HH:mm:ss');
							},
							width: '10rem'
						},
						{
							label: 'End Time',
							fieldname: 'end',
							class: 'text-gray-600',
							format(value) {
								if (!value) return;
								return dayjs(value).format('DD/MM/YYYY HH:mm:ss');
							},
							width: '10rem'
						}
					]
				}
			}
		],
		actions() {
			return [
				{
					label: 'Update available',
					variant: 'solid'
				}
			];
		}
	},
	routes: [
		{
			name: 'Bench Deploy',
			path: 'deploy/:id',
			component: () => import('../pages/BenchDeploy.vue')
		},
		{
			name: 'Bench Job',
			path: 'job/:id',
			component: () => import('../pages/JobPage.vue')
		}
	]
};
