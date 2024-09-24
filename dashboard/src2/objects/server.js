import { defineAsyncComponent, h } from 'vue';
import LucideAppWindow from '~icons/lucide/app-window';
import { planTitle, duration, userCurrency } from '../utils/format';
import ServerActions from '../components/server/ServerActions.vue';
import { icon } from '../utils/components';
import { trialDays } from '../utils/site';
import { getTeam } from '../data/team';
import { tagTab } from './common/tags';
import router from '../router';
import { jobTab } from './common/jobs';

export default {
	doctype: 'Server',
	whitelistedMethods: {
		increaseDiskSize: 'increase_disk_size_for_server',
		configureAutoAddStorage: 'configure_auto_add_storage',
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
		filterControls() {
			return [
				{
					type: 'select',
					label: 'Status',
					fieldname: 'status',
					options: ['', 'Active', 'Pending']
				},
				{
					type: 'select',
					label: 'Region',
					fieldname: 'cluster',
					options: [
						'',
						'Bahrain',
						'Cape Town',
						'Frankfurt',
						'KSA',
						'London',
						'Mumbai',
						'Singapore',
						'UAE',
						'Virginia',
						'Zurich'
					]
				}
			];
		},
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
							condition: () => $team.doc?.is_desk_user,
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
								server.doc.status === 'Active' && $team.doc?.is_desk_user,
							onClick() {
								window.open(`https://${server.doc.name}`, '_blank');
							}
						},
						{
							label: 'Impersonate Team',
							icon: defineAsyncComponent(() =>
								import('~icons/lucide/venetian-mask')
							),
							condition: () => window.is_system_user,
							onClick() {
								switchToTeam(server.doc.team);
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
				label: 'Sites',
				icon: icon(LucideAppWindow),
				route: 'sites',
				type: 'list',
				list: {
					doctype: 'Site',
					filters: server => {
						return { server: server.doc.name };
					},
					fields: [
						'plan.plan_title as plan_title',
						'plan.price_usd as price_usd',
						'plan.price_inr as price_inr',
						'group.title as group_title',
						'group.public as group_public',
						'group.team as group_team',
						'group.version as version',
						'trial_end_date'
					],
					orderBy: 'creation desc',
					searchField: 'host_name',
					route(row) {
						return { name: 'Site Detail', params: { name: row.name } };
					},
					filterControls() {
						return [
							{
								type: 'select',
								label: 'Status',
								fieldname: 'status',
								options: ['', 'Active', 'Inactive', 'Suspended', 'Broken']
							},
							{
								type: 'link',
								label: 'Version',
								fieldname: 'group.version',
								options: {
									doctype: 'Frappe Version'
								}
							},
							{
								type: 'link',
								label: 'Bench Group',
								fieldname: 'group',
								options: {
									doctype: 'Release Group'
								}
							},
							{
								type: 'link',
								label: 'Tag',
								fieldname: 'tags.tag',
								options: {
									doctype: 'Press Tag',
									filters: {
										doctype_name: 'Site'
									}
								}
							}
						];
					},
					columns: [
						{
							label: 'Site',
							fieldname: 'host_name',
							width: 1.5,
							class: 'font-medium',
							format(value, row) {
								return value || row.name;
							}
						},
						{ label: 'Status', fieldname: 'status', type: 'Badge', width: 0.6 },
						{
							label: 'Plan',
							fieldname: 'plan',
							width: 0.85,
							format(value, row) {
								if (row.trial_end_date) {
									return trialDays(row.trial_end_date);
								}
								let $team = getTeam();
								if (row.price_usd > 0) {
									let india = $team.doc.country == 'India';
									let formattedValue = userCurrency(
										india ? row.price_inr : row.price_usd,
										0
									);
									return `${formattedValue}/mo`;
								}
								return row.plan_title;
							}
						},
						{
							label: 'Bench Group',
							fieldname: 'group_title',
							width: '15rem'
						},
						{
							label: 'Version',
							fieldname: 'version',
							width: 0.5
						}
					]
				}
			},
			{
				label: 'Bench Groups',
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
					filterControls() {
						return [
							{
								type: 'link',
								label: 'Version',
								fieldname: 'version',
								options: {
									doctype: 'Frappe Version'
								}
							},
							{
								type: 'link',
								label: 'Tag',
								fieldname: 'tags.tag',
								options: {
									doctype: 'Press Tag',
									filters: {
										doctype_name: 'Release Group'
									}
								}
							}
						];
					},
					route(row) {
						return {
							name: 'Release Group Detail',
							params: { name: row.name }
						};
					},
					primaryAction({ listResource: benches, documentResource: server }) {
						return {
							label: 'New Bench Group',
							slots: {
								prefix: icon('plus')
							},
							onClick() {
								router.push({
									name: 'Server New Release Group',
									params: { server: server.doc.name }
								});
							}
						};
					}
				}
			},
			jobTab('Server'),
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
