import { defineAsyncComponent, h } from 'vue';
import { icon } from '../utils/components';
import { duration } from '../utils/format';
import { getTeam } from '../data/team';

export default {
	doctype: 'Server',
	whitelistedMethods: {
		changePlan: 'change_plan'
	},
	list: {
		route: '/servers',
		title: 'Servers',
		fields: [
			'plan.plan_title as plan_title',
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
				width: 1.5
			},
			{ label: 'Status', fieldname: 'status', type: 'Badge', width: 0.8 },
			{
				label: 'Plan',
				width: 1,
				format(value, row) {
					let $team = getTeam();
					if (row.price_usd > 0) {
						let india = $team.doc.country == 'India';
						let currencySymbol = $team.doc.currency === 'INR' ? '₹' : '$';
						return `${currencySymbol}${
							india ? row.price_inr : row.price_usd
						} /mo`;
					}
					return row.plan_title;
				}
			},
			{
				label: 'Region',
				fieldname: 'cluster',
				width: 1,
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
					// router.push({ name: 'NewServer' });
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
					return { servers: server.doc.name };
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
							class: 'text-gray-600',
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
							class: 'text-gray-600',
							width: 0.25
						}
					],
					route(row) {
						return {
							name: 'Release Group Detail',
							params: { name: row.name }
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
							params: { id: row.name, server: row.server }
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
							fieldname: 'job_id',
							class: 'text-gray-600'
						},
						{
							label: 'Duration',
							fieldname: 'duration',
							class: 'text-gray-600',
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
				label: 'Plays',
				icon: icon('play'),
				childrenRoutes: ['Server Play'],
				route: 'plays',
				type: 'list',
				list: {
					doctype: 'Ansible Play',
					filters: server => {
						return { server: server.doc.name };
					},
					route(row) {
						return {
							name: 'Server Play',
							params: { id: row.name, server: row.server }
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
							type: 'Badge'
						},
						{
							label: 'Job ID',
							fieldname: 'job_id',
							class: 'text-gray-600'
						},
						{
							label: 'Duration',
							fieldname: 'duration',
							class: 'text-gray-600',
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
			}
		]
	},
	routes: [
		{
			name: 'Server Job',
			path: 'job/:id',
			component: () => import('../pages/JobPage.vue')
		},
		{
			name: 'Server Play',
			path: 'play/:id',
			component: () => import('../pages/PlayPage.vue')
		}
	]
};
