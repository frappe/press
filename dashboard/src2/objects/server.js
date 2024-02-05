import { defineAsyncComponent, h } from 'vue';
import { toast } from 'vue-sonner';
import { confirmDialog, icon } from '../utils/components';
import { duration } from '../utils/format';
import { getTeam } from '../data/team';
import router from '../router';

export default {
	doctype: 'Server',
	whitelistedMethods: {
		changePlan: 'change_plan',
		reboot: 'reboot',
		rename: 'rename'
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
					router.push({ name: 'NewServer' });
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
							condition: () => server.doc.status === 'Active',
							onClick() {
								window.open(`https://${server.doc.name}`, '_blank');
							}
						},
						{
							label: 'Rename Server',
							condition: () => server.doc.status === 'Active',
							icon: icon('edit'),
							onClick() {
								confirmDialog({
									title: 'Rename Server',
									fields: [
										{
											label: 'Enter new title for the server',
											fieldname: 'title'
										}
									],
									primaryAction: {
										label: 'Update Title'
									},
									onSuccess({ hide, values }) {
										if (server.rename.loading) return;
										toast.promise(
											server.rename.submit(
												{
													title: values.title
												},
												{
													onSuccess() {
														hide();
													}
												}
											),
											{
												loading: 'Updating title...',
												success: 'Title updated',
												error: 'Failed to update title'
											}
										);
									}
								});
							}
						},
						{
							label: 'Reboot Server',
							condition: () => server.doc.status === 'Active',
							icon: icon('rotate-ccw'),
							onClick() {
								confirmDialog({
									title: 'Reboot Server',
									message: `Are you sure you want to reboot the server <b>${server.doc.name}</b>?`,
									fields: [
										{
											label: 'Please type the server name to confirm',
											fieldname: 'confirmServerName'
										}
									],
									primaryAction: {
										label: 'Reboot Server'
									},
									onSuccess({ hide, values }) {
										if (server.reboot.loading) return;
										if (values.confirmServerName !== server.doc.name) {
											throw new Error('Server name does not match');
										}
										toast.promise(
											server.reboot.submit(null, {
												onSuccess() {
													hide();
												}
											}),
											{
												loading: 'Rebooting...',
												success: 'Server rebooted',
												error: 'Failed to reboot server'
											}
										);
									}
								});
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
					},
					primaryAction({ listResource: benches, documentResource: server }) {
						return {
							label: 'New Bench',
							slots: {
								prefix: icon('plus')
							},
							onClick() {
								router.push({
									name: 'NewServerBench',
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
