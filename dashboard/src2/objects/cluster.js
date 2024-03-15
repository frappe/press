import HelpIcon from '~icons/lucide/help-circle';
import { defineAsyncComponent, h } from 'vue';
import { Button } from 'frappe-ui';
import ServerActions from '../components/server/ServerActions.vue';
import { userCurrency, bytes, pricePerDay, planTitle } from '../utils/format';
import { icon } from '../utils/components';
import { duration } from '../utils/format';
import { getTeam } from '../data/team';
import { tagTab } from './common/tags';
import router from '../router';

export default {
	doctype: 'Cluster',
	list: {
		route: '/clusters',
		title: 'Cluster',
		orderBy: 'creation desc',
		columns: [
			{
				label: 'Name',
				fieldname: 'title',
				width: 1
			},
			{ label: 'Status', fieldname: 'status', type: 'Badge', width: 0.8 },
			{ label: 'Description', fieldname: 'description', width: 2 },
			{ label: 'Provider', fieldname: 'cloud_provider', width: 1 },
			{
				label: 'Created On',
				fieldname: 'creation',
				type: 'Timestamp',
				width: 1
			}
		],
		primaryAction({ listResource: servers }) {
			return {
				label: 'New Cluster',
				variant: 'solid',
				slots: {
					prefix: icon('plus')
				},
				onClick() {
					router.push({ name: 'New Cluster' });
				}
			};
		}
	},
	detail: {
		titleField: 'name',
		route: '/clusters/:name',
		statusBadge({ documentResource: cluster }) {
			return {
				label: cluster.doc.status
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
					import('../components/cluster/ClusterOverview.vue')
				),
				props: cluster => {
					return { cluster: cluster.doc.name };
				}
			}
			// {
			// 	label: 'Analytics',
			// 	icon: icon('bar-chart-2'),
			// 	route: 'analytics',
			// 	type: 'Component',
			// 	component: defineAsyncComponent(() =>
			// 		import('../../src/views/server/ServerAnalytics.vue')
			// 	),
			// 	props: server => {
			// 		return {
			// 			serverName: server.doc.name,
			// 			dbServerName: server.doc.database_server
			// 		};
			// 	}
			// },
			// {
			// 	label: 'Benches',
			// 	icon: icon('package'),
			// 	route: 'benches',
			// 	type: 'list',
			// 	list: {
			// 		doctype: 'Release Group',
			// 		filters: server => {
			// 			return { server: server.doc.name };
			// 		},
			// 		fields: [{ apps: ['app'] }, { servers: ['server'] }],
			// 		columns: [
			// 			{ label: 'Title', fieldname: 'title' },
			// 			{
			// 				label: 'Status',
			// 				fieldname: 'active_benches',
			// 				type: 'Badge',
			// 				width: 0.5,
			// 				format: (value, row) => {
			// 					if (!value) return 'Awaiting Deploy';
			// 					else return 'Active';
			// 				}
			// 			},
			// 			{
			// 				label: 'Version',
			// 				fieldname: 'version',
			// 				class: 'text-gray-600',
			// 				width: 0.5
			// 			},
			// 			{
			// 				label: 'Apps',
			// 				fieldname: 'app',
			// 				format: (value, row) => {
			// 					return (row.apps || []).map(d => d.app).join(', ');
			// 				},
			// 				width: '25rem'
			// 			},
			// 			{
			// 				label: 'Sites',
			// 				fieldname: 'site_count',
			// 				class: 'text-gray-600',
			// 				width: 0.25
			// 			}
			// 		],
			// 		route(row) {
			// 			return {
			// 				name: 'Release Group Detail',
			// 				params: { name: row.name }
			// 			};
			// 		},
			// 		primaryAction({ listResource: benches, documentResource: server }) {
			// 			return {
			// 				label: 'New Bench',
			// 				slots: {
			// 					prefix: icon('plus')
			// 				},
			// 				onClick() {
			// 					router.push({
			// 						name: 'Server New Bench',
			// 						params: { server: server.doc.name }
			// 					});
			// 				}
			// 			};
			// 		}
			// 	}
			// },
			// {
			// 	label: 'Jobs',
			// 	icon: icon('truck'),
			// 	childrenRoutes: ['Server Job'],
			// 	route: 'jobs',
			// 	type: 'list',
			// 	list: {
			// 		doctype: 'Agent Job',
			// 		filters: server => {
			// 			return { server: server.doc.name };
			// 		},
			// 		route(row) {
			// 			return {
			// 				name: 'Server Job',
			// 				params: { id: row.name }
			// 			};
			// 		},
			// 		orderBy: 'creation desc',
			// 		fields: ['server', 'end'],
			// 		columns: [
			// 			{
			// 				label: 'Job Type',
			// 				fieldname: 'job_type',
			// 				width: 2
			// 			},
			// 			{
			// 				label: 'Status',
			// 				fieldname: 'status',
			// 				type: 'Badge'
			// 			},
			// 			{
			// 				label: 'Job ID',
			// 				fieldname: 'job_id',
			// 				class: 'text-gray-600'
			// 			},
			// 			{
			// 				label: 'Duration',
			// 				fieldname: 'duration',
			// 				class: 'text-gray-600',
			// 				format(value, row) {
			// 					if (row.job_id === 0 || !row.end) return;
			// 					return duration(value);
			// 				}
			// 			},
			// 			{
			// 				label: 'Created By',
			// 				fieldname: 'owner'
			// 			},
			// 			{
			// 				label: '',
			// 				fieldname: 'creation',
			// 				type: 'Timestamp',
			// 				align: 'right'
			// 			}
			// 		]
			// 	}
			// },
			// {
			// 	label: 'Plays',
			// 	icon: icon('play'),
			// 	childrenRoutes: ['Server Play'],
			// 	route: 'plays',
			// 	type: 'list',
			// 	list: {
			// 		doctype: 'Ansible Play',
			// 		filters: server => {
			// 			return {
			// 				server: ['in', [server.doc.name, server.doc.database_server]]
			// 			};
			// 		},
			// 		route(row) {
			// 			return {
			// 				name: 'Server Play',
			// 				params: { id: row.name }
			// 			};
			// 		},
			// 		orderBy: 'creation desc',
			// 		fields: ['server', 'end'],
			// 		columns: [
			// 			{
			// 				label: 'Play',
			// 				fieldname: 'play',
			// 				width: 2
			// 			},
			// 			{
			// 				label: 'Status',
			// 				fieldname: 'status',
			// 				type: 'Badge',
			// 				width: 0.5
			// 			},
			// 			{
			// 				label: 'Server',
			// 				fieldname: 'server',
			// 				width: 2
			// 			},
			// 			{
			// 				label: 'Duration',
			// 				fieldname: 'duration',
			// 				width: 0.5,
			// 				class: 'text-gray-600',
			// 				format(value, row) {
			// 					if (row.job_id === 0 || !row.end) return;
			// 					return duration(value);
			// 				}
			// 			},
			// 			{
			// 				label: '',
			// 				fieldname: 'creation',
			// 				type: 'Timestamp',
			// 				align: 'right'
			// 			}
			// 		]
			// 	}
			// },
			// {
			// 	label: 'Actions',
			// 	icon: icon('activity'),
			// 	route: 'actions',
			// 	type: 'Component',
			// 	component: ServerActions,
			// 	props: server => {
			// 		return { server: server.doc.name };
			// 	}
			// },
			// tagTab()
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
