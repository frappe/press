import { defineAsyncComponent } from 'vue';
import { toast } from 'vue-sonner';
import { confirmDialog, icon } from '../utils/components';
import { duration } from '../utils/format';
import { getTeam } from '../data/team';
import { tagTab } from './common/tags';
import router from '../router';

export default {
	doctype: 'Database Server',
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
		title: 'Servers'
	},
	detail: {
		titleField: 'name',
		route: '/database-servers/:name',
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
							label: 'Switch to App Server',
							icon: icon('repeat'),
							condition: () => server.doctype === 'Database Server',
							onClick() {
								router.push({
									name: 'Server Detail Overview',
									params: {
										name: server.doc.name.replace('m', 'f')
									}
								});
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
						},
						{
							label: 'Drop Server',
							condition: () => server.doc.status === 'Active',
							icon: icon('trash-2'),
							onClick() {
								confirmDialog({
									title: 'Drop Server',
									message: `Are you sure you want to drop your servers?<br>Both the Application server (<b>${server.doc.name.replace(
										'm',
										'f'
									)}</b>) and Database server (<b>${
										server.doc.name
									}</b>)will be archived.<br>This action cannot be undone.`,
									fields: [
										{
											label: 'Please type the server name to confirm',
											fieldname: 'confirmServerName'
										}
									],
									primaryAction: {
										label: 'Drop Server',
										theme: 'red'
									},
									onSuccess({ hide, values }) {
										if (server.dropServer.loading) return;
										if (values.confirmServerName !== server.doc.name) {
											throw new Error('Server name does not match');
										}
										toast.promise(server.dropServer.submit().then(hide), {
											loading: 'Dropping...',
											success: 'Server dropped',
											error: 'Failed to drop server'
										});
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
					return { server: server.doc.name, serverType: server.doctype };
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
					return { serverName: server.doc.name };
				}
			},
			{
				label: 'Plays',
				icon: icon('play'),
				childrenRoutes: ['Database Server Play'],
				route: 'plays',
				type: 'list',
				list: {
					doctype: 'Ansible Play',
					filters: server => {
						return { server: server.doc.name };
					},
					route(row) {
						return {
							name: 'Database Server Play',
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
			tagTab()
		]
	},
	routes: [
		{
			name: 'Database Server Play',
			path: 'play/:id',
			component: () => import('../pages/PlayPage.vue')
		}
	]
};
