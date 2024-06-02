import { defineAsyncComponent, h } from 'vue';
import ServerActions from '../components/server/ServerActions.vue';
import { planTitle, duration } from '../utils/format';
import { icon } from '../utils/components';
import { getTeam } from '../data/team';
import { tagTab } from './common/tags';
import router from '../router';

export default {
	doctype: 'Server',
	whitelistedMethods: {
		changePlan: 'change_plan',
		reboot: 'reboot',
		rename: 'rename',
		dropServer: 'drop_server',
		addTag: 'add_resource_tag',
		removeTag: 'remove_resource_tag'
	},
	list: {
		route: '/servers',
		title: 'Servers',
		fields: [
			'title',
			'database_server',
			'plan.title as plan_title',
			'plan.price_usd as price_usd',
			'plan.price_inr as price_inr',
			'cluster.image as cluster_image',
			'cluster.title as cluster_title'
		],
		orderBy: 'creation desc',
		columns: [
			{
				label: 'Server',
				fieldname: 'name',
				width: 1.5,
				class: 'font-medium',
				format(value, row) {
					return row.title || value;
				}
			},
			{ label: 'Status', fieldname: 'status', type: 'Badge', width: 0.8 },
			{
				label: 'App Server Plan',
				format(value, row) {
					return planTitle(row);
				}
			},
			{
				label: 'Database Server Plan',
				fieldname: 'db_plan',
				format(value) {
					if (!value) return '';
					return planTitle(value);
				}
			},
			{
				label: 'Region',
				fieldname: 'cluster',
				format(value, row) {
					return row.cluster_title || value;
				},
				prefix(row) {
					return h('img', {
						src: row.cluster_image,
						class: 'w-4 h-4',
						alt: row.cluster_title
					});
				}
			}
		],
		primaryAction({ listResource: servers }) {
			return {
				label: 'New Server',
				variant: 'solid',
				slots: {
					prefix: icon('plus')
				},
				onClick() {
					router.push({ name: 'New Server' });
				}
			};
		}
	},
	detail: {
		titleField: 'name',
		route: '/servers/:name',
		statusBadge({ documentResource: server }) {
			return {
				label: server.doc.status
			};
		},
		breadcrumbs({ documentResource: server }) {
			return [
				{
					label: 'Servers',
					route: '/servers'
				},
				{
					label: server.doc.title || server.doc.name,
					route: `/servers/${server.doc.name}`
				}
			];
		},
		actions({ documentResource: server }) {
			let $team = getTeam();

			return [
				{
					label: 'Options',
					button: {
						label: 'Options',
						slots: {
							icon: icon('more-horizontal')
						}
					},
					options: [
						{
							label: 'View in Desk',
							icon: icon('external-link'),
							condition: () => $team.doc.is_desk_user,
							onClick() {
								window.open(
									`${window.location.protocol}//${
										window.location.host
									}/app/${server.doctype.replace(' ', '-').toLowerCase()}/${
										server.doc.name
									}`,
									'_blank'
								);
							}
						},
						{
							label: 'Visit Server',
							icon: icon('external-link'),
							condition: () =>
								server.doc.status === 'Active' && $team.doc.is_desk_user,
							onClick() {
								window.open(`https://${server.doc.name}`, '_blank');
							}
						}
					]
				}
			];
		},
		tabs: [
			{
				label: 'Overview',
				icon: icon('home'),
				route: 'overview',
				type: 'Component',
				component: defineAsyncComponent(() =>
					import('../components/server/ServerOverview.vue')
				),
				props: server => {
					return { server: server.doc.name };
				}
			},
			{
				label: 'Analytics',
				icon: icon('bar-chart-2'),
				route: 'analytics',
				type: 'Component',
				component: defineAsyncComponent(() =>
					import('../../src/views/server/ServerAnalytics.vue')
				),
				props: server => {
					return {
						serverName: server.doc.name
					};
				}
			},
			{
				label: 'Benches',
				icon: icon('package'),
				route: 'benches',
				type: 'list',
				list: {
					doctype: 'Release Group',
					filters: server => {
						return { server: server.doc.name };
					},
					fields: [{ apps: ['app'] }, { servers: ['server'] }],
					columns: [
						{ label: 'Title', fieldname: 'title' },
						{
							label: 'Status',
							fieldname: 'active_benches',
							type: 'Badge',
							width: 0.5,
							format: (value, row) => {
								if (!value) return 'Awaiting Deploy';
								else return 'Active';
							}
						},
						{
							label: 'Version',
							fieldname: 'version',
							width: 0.5
						},
						{
							label: 'Apps',
							fieldname: 'app',
							format: (value, row) => {
								return (row.apps || []).map(d => d.app).join(', ');
							},
							width: '25rem'
						},
						{
							label: 'Sites',
							fieldname: 'site_count',
							width: 0.25
						}
					],
					route(row) {
						return {
							name: 'Release Group Detail',
							params: { name: row.name }
						};
					},
					primaryAction({ listResource: benches, documentResource: server }) {
						return {
							label: 'New Bench',
							slots: {
								prefix: icon('plus')
							},
							onClick() {
								router.push({
									name: 'Server New Bench',
									params: { server: server.doc.name }
								});
							}
						};
					}
				}
			},
			{
				label: 'Jobs',
				icon: icon('truck'),
				childrenRoutes: ['Server Job'],
				route: 'jobs',
				type: 'list',
				list: {
					doctype: 'Agent Job',
					filters: server => {
						return { server: server.doc.name };
					},
					route(row) {
						return {
							name: 'Server Job',
							params: { id: row.name }
						};
					},
					orderBy: 'creation desc',
					fields: ['server', 'end'],
					columns: [
						{
							label: 'Job Type',
							fieldname: 'job_type',
							width: 2
						},
						{
							label: 'Status',
							fieldname: 'status',
							type: 'Badge'
						},
						{
							label: 'Job ID',
							fieldname: 'job_id'
						},
						{
							label: 'Duration',
							fieldname: 'duration',
							format(value, row) {
								if (row.job_id === 0 || !row.end) return;
								return duration(value);
							}
						},
						{
							label: 'Created By',
							fieldname: 'owner'
						},
						{
							label: '',
							fieldname: 'creation',
							type: 'Timestamp',
							align: 'right'
						}
					]
				}
			},
			{
				label: 'Plays',
				icon: icon('play'),
				childrenRoutes: ['Server Play'],
				route: 'plays',
				type: 'list',
				list: {
					doctype: 'Ansible Play',
					filterControls({ documentResource: server }) {
						return [
							{
								type: 'select',
								label: 'Server',
								fieldname: 'server',
								options: [
									server.doc.name,
									server.doc.database_server,
									server.doc.replication_server
								].filter(Boolean)
							}
						];
					},
					filters: server => {
						return {
							server: [
								'in',
								[
									server.doc.name,
									server.doc.database_server,
									server.doc.replication_server
								].filter(Boolean)
							]
						};
					},
					route(row) {
						return {
							name: 'Server Play',
							params: { id: row.name }
						};
					},
					orderBy: 'creation desc',
					fields: ['server', 'end'],
					columns: [
						{
							label: 'Play',
							fieldname: 'play',
							width: 2
						},
						{
							label: 'Status',
							fieldname: 'status',
							type: 'Badge',
							width: 0.5
						},
						{
							label: 'Server',
							fieldname: 'server',
							width: 2
						},
						{
							label: 'Duration',
							fieldname: 'duration',
							width: 0.5,
							format(value, row) {
								if (row.job_id === 0 || !row.end) return;
								return duration(value);
							}
						},
						{
							label: '',
							fieldname: 'creation',
							type: 'Timestamp',
							align: 'right'
						}
					]
				}
			},
			{
				label: 'Actions',
				icon: icon('sliders'),
				route: 'actions',
				type: 'Component',
				component: ServerActions,
				props: server => {
					return { server: server.doc.name };
				}
			},
			tagTab()
		]
	},
	routes: [
		{
			name: 'Server Job',
			path: 'jobs/:id',
			component: () => import('../pages/JobPage.vue')
		},
		{
			name: 'Server Play',
			path: 'plays/:id',
			component: () => import('../pages/PlayPage.vue')
		}
	]
};
