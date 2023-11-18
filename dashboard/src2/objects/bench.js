import { defineAsyncComponent, h } from 'vue';
import { toast } from 'vue-sonner';
import dayjs from '../utils/dayjs';
import { duration } from '../utils/format';
import { icon, renderDialog } from '../utils/components';
import teamResource from '../data/team';
import ChangeAppBranchDialog from '../components/bench/ChangeAppBranchDialog.vue';
import AddAppDialog from '../components/bench/AddAppDialog.vue';

export default {
	doctype: 'Release Group',
	whitelistedMethods: {
		removeApp: 'remove_app',
		changeAppBranch: 'change_app_branch',
		fetchLatestAppUpdates: 'fetch_latest_app_update'
	},
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
				label: 'Apps',
				icon: icon('grid'),
				route: 'apps',
				type: 'list',
				list: {
					resource({ documentResource: group }) {
						return {
							type: 'list',
							doctype: 'Release Group App',
							cache: ['ObjectList', 'Release Group App'],
							parent: 'Release Group',
							filters: {
								parenttype: 'Release Group',
								parent: group.name
							},
							auto: true
						};
					},
					columns: [
						{
							label: 'App',
							fieldname: 'title',
							width: 1
						},
						{
							label: 'Branch',
							fieldname: 'branch',
							type: 'Badge',
							width: 1
						},
						{
							label: 'Update Available',
							fieldname: 'update_available',
							type: 'Icon',
							Icon(value) {
								return value ? 'check' : '';
							},
							width: 1
						}
					],
					rowActions({ row, listResource: apps, documentResource: group }) {
						let team = teamResource.data;
						return [
							{
								label: 'View in Desk',
								condition: () => team.is_desk_user,
								onClick() {
									window.open(
										`${window.location.protocol}//${window.location.host}/app/release-group/${group.name}`,
										'_blank'
									);
								}
							},
							{
								label: 'Fetch Latest Updates',
								onClick() {
									toast.promise(
										group.fetchLatestAppUpdates.submit({
											app: row.name
										}),
										{
											loading: `Fetching Latest Updates for ${row.title}...`,
											success: `Latest Updates Fetched for ${row.title}`,
											error: e => {
												return e.messages.length
													? e.messages.join('\n')
													: e.message;
											}
										}
									);
								}
							},
							{
								label: 'Change Branch',
								onClick() {
									renderDialog(
										h(ChangeAppBranchDialog, {
											bench: group.name,
											app: row,
											onBranchChange() {
												apps.reload();
											}
										})
									);
								}
							},
							{
								label: 'Remove App',
								condition: () => row.name !== 'frappe',
								onClick() {
									if (group.removeApp.loading) return;
									toast.promise(
										group.removeApp.submit({
											app: row.name
										}),
										{
											loading: 'Removing App...',
											success: () => {
												apps.reload();
												return 'App Removed';
											},
											error: e => {
												return e.messages.length
													? e.messages.join('\n')
													: e.message;
											}
										}
									);
								}
							},
							{
								label: 'Visit Repo',
								onClick() {
									window.open(
										`${row.repository_url}/tree/${row.branch}`,
										'_blank'
									);
								}
							}
						];
					},
					primaryAction({ listResource: apps, documentResource: group }) {
						return {
							label: 'Add App',
							variant: 'solid',
							slots: {
								prefix: icon('plus')
							},
							onClick() {
								renderDialog(
									h(AddAppDialog, {
										benchName: group.name,
										onAppAdd() {
											apps.reload();
										}
									})
								);
							}
						};
					}
				}
			},
			{
				label: 'Deploys',
				route: 'deploys',
				icon: icon('package'),
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
			},
			{
				label: 'Config',
				icon: icon('code'),
				route: 'bench-config',
				type: 'Component',
				component: defineAsyncComponent(() =>
					import('../../src/views/bench/BenchConfig.vue')
				),
				props: group => ({ bench: group.doc })
			}
		],
		actions(context) {
			let { documentResource: group } = context;
			return [
				{
					label: 'Update available',
					variant: 'solid',
					condition: () => group.doc.status === 'Update Available'
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
