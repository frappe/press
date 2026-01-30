import { defineAsyncComponent, h } from 'vue';
import { toast } from 'vue-sonner';
import LucideAppWindow from '~icons/lucide/app-window';
import LucideVenetianMask from '~icons/lucide/venetian-mask';
import ServerActions from '../components/server/ServerActions.vue';
import { getTeam } from '../data/team';
import router from '../router';
import { confirmDialog, icon, renderDialog } from '../utils/components';
import { isMobile } from '../utils/device';
import { date, duration, planTitle, userCurrency } from '../utils/format';
import { getQueryParam, setQueryParam } from '../utils/index';
import { trialDays } from '../utils/site';
import { getJobsTab } from './common/jobs';
import { tagTab } from './common/tags';

export default {
	doctype: 'Server',
	whitelistedMethods: {
		increaseDiskSize: 'increase_disk_size_for_server',
		configureAutoAddStorage: 'configure_auto_add_storage',
		changePlan: 'change_plan',
		toggleAutoIncreaseStorage: 'toggle_auto_increase_storage',
		reboot: 'reboot',
		rename: 'rename',
		cleanup: 'cleanup_unused_files',
		dropServer: 'drop_server',
		addTag: 'add_resource_tag',
		removeTag: 'remove_resource_tag',
		deleteSnapshot: 'delete_snapshot',
		lockSnapshot: 'lock_snapshot',
		unlockSnapshot: 'unlock_snapshot',
		setupSecondaryServer: 'setup_secondary_server',
		teardownSecondaryServer: 'teardown_secondary_server',
		scaleUp: 'scale_up',
		scaleDown: 'scale_down',
		addAutomatedScalingTriggers: 'add_automated_scaling_triggers',
		removeAutomatedScalingTriggers: 'remove_automated_scaling_triggers',
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
			'cluster.title as cluster_title',
			'is_unified_server',
		],
		searchField: 'title',
		filterControls() {
			return [
				{
					type: 'select',
					label: 'Status',
					fieldname: 'status',
					options: ['', 'Active', 'Pending', 'Archived'],
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
						'Zurich',
					],
				},
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
				},
			},
			{ label: 'Status', fieldname: 'status', type: 'Badge', width: 0.8 },
			{
				label: 'App Server Plan',
				format(value, row) {
					return planTitle(row);
				},
			},
			{
				label: 'Database Server Plan',
				fieldname: 'db_plan',
				format(value, row) {
					if (!value || row.is_unified_server) return '';
					return planTitle(value);
				},
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
						alt: row.cluster_title,
					});
				},
			},
		],
		primaryAction({ listResource: servers }) {
			return {
				label: 'New Server',
				variant: 'solid',
				slots: {
					prefix: icon('plus'),
				},
				onClick() {
					router.push({ name: 'New Server' });
				},
			};
		},
		banner({ listResource: servers }) {
			if (!servers.data?.length) {
				return {
					title: 'Learn how to create a new dedicated server',
					button: {
						label: 'Read docs',
						variant: 'outline',
						link: 'https://docs.frappe.io/cloud/servers/new',
					},
				};
			}
		},
	},
	detail: {
		titleField: 'name',
		route: '/servers/:name',
		statusBadge({ documentResource: server }) {
			return {
				label: server.doc.status,
			};
		},
		breadcrumbs({ documentResource: server }) {
			return [
				{
					label: 'Servers',
					route: '/servers',
				},
				{
					label: server.doc.title || server.doc.name,
					route: `/servers/${server.doc.name}`,
				},
			];
		},
		actions({ documentResource: server }) {
			let $team = getTeam();

			if (server?.doc?.status === 'Archived') {
				return [];
			}

			return [
				{
					label: 'Impersonate Server Owner',
					title: 'Impersonate Server Owner', // for label to pop-up on hover
					slots: {
						icon: icon(LucideVenetianMask),
					},
					condition: () =>
						$team.doc?.is_desk_user && server.doc.team !== $team.name,
					onClick() {
						switchToTeam(server.doc.team);
					},
				},
				{
					label: 'Options',
					button: {
						label: 'Options',
						slots: {
							icon: icon('more-horizontal'),
						},
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
									'_blank',
								);
							},
						},
						{
							label: 'View DB in Desk',
							icon: icon('external-link'),
							condition: () => $team.doc?.is_desk_user,
							onClick() {
								window.open(
									`${window.location.protocol}//${
										window.location.host
									}/app/database-server/${server.doc.database_server}`,
									'_blank',
								);
							},
						},
						{
							label: 'View Replication DB in Desk',
							icon: icon('external-link'),
							condition: () =>
								$team.doc?.is_desk_user && server.doc.replication_server,
							onClick() {
								window.open(
									`${window.location.protocol}//${
										window.location.host
									}/app/database-server/${server.doc.replication_server}`,
									'_blank',
								);
							},
						},
						{
							label: 'Visit Server',
							icon: icon('external-link'),
							condition: () =>
								server.doc.status === 'Active' && $team.doc?.is_desk_user,
							onClick() {
								window.open(`https://${server.doc.name}`, '_blank');
							},
						},
					],
				},
			];
		},
		tabs: [
			{
				label: 'Overview',
				icon: icon('home'),
				condition: (server) => {
					return server.doc?.status !== 'Archived';
				},
				route: 'overview',
				type: 'Component',
				component: defineAsyncComponent(
					() => import('../components/server/ServerOverview.vue'),
				),
				props: (server) => {
					return { server: server.doc.name };
				},
			},
			{
				label: 'Analytics',
				icon: icon('bar-chart-2'),
				condition: (server) => server.doc?.status !== 'Archived',
				route: 'analytics',
				type: 'Component',
				component: defineAsyncComponent(
					() => import('../components/server/ServerCharts.vue'),
				),
				props: (server) => {
					return {
						serverName: server.doc.name,
					};
				},
			},
			{
				label: 'Bench Analytics',
				icon: icon('bar-chart-2'),
				condition: (server) => server.doc?.status !== 'Archived',
				route: 'bench-group-analytics',
				type: 'Component',
				component: defineAsyncComponent(
					() => import('../components/server/ReleaseGroupCharts.vue'),
				),
				props: (server) => {
					return { serverName: server.doc.name };
				},
			},
			{
				label: 'Firewall',
				icon: icon('shield'),
				condition: (server) => {
					return (
						server.doc?.status !== 'Archived' && !server.doc?.is_self_hosted
					);
				},
				route: 'firewall',
				type: 'Component',
				component: defineAsyncComponent(
					() => import('../components/server/ServerFirewall.vue'),
				),
				props: (server) => {
					return {
						id: server.doc.name,
					};
				},
			},
			{
				label: 'Sites',
				icon: icon(LucideAppWindow),
				condition: (server) => {
					return server.doc?.status !== 'Archived';
				},
				route: 'sites',
				type: 'list',
				list: {
					doctype: 'Site',
					filters: (server) => {
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
						'trial_end_date',
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
								options: ['', 'Active', 'Inactive', 'Suspended', 'Broken'],
							},
							{
								type: 'link',
								label: 'Version',
								fieldname: 'group.version',
								options: {
									doctype: 'Frappe Version',
								},
							},
							{
								type: 'link',
								label: 'Bench Group',
								fieldname: 'group',
								options: {
									doctype: 'Release Group',
								},
							},
							{
								type: 'link',
								label: 'Tag',
								fieldname: 'tags.tag',
								options: {
									doctype: 'Press Tag',
									filters: {
										doctype_name: 'Site',
									},
								},
							},
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
							},
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
										0,
									);
									return `${formattedValue}/mo`;
								}
								return row.plan_title;
							},
						},
						{
							label: 'Bench Group',
							fieldname: 'group_title',
							width: '15rem',
						},
						{
							label: 'Version',
							fieldname: 'version',
							width: 0.5,
						},
					],
				},
			},
			{
				label: 'Bench Groups',
				icon: icon('package'),
				condition: (server) => {
					return server.doc?.status !== 'Archived';
				},
				route: 'groups',
				type: 'list',
				list: {
					doctype: 'Release Group',
					filters: (server) => {
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
							},
						},
						{
							label: 'Version',
							fieldname: 'version',
							width: 0.5,
						},
						{
							label: 'Apps',
							fieldname: 'app',
							format: (value, row) => {
								return (row.apps || []).map((d) => d.app).join(', ');
							},
							width: '25rem',
						},
						{
							label: 'Sites',
							fieldname: 'site_count',
							width: 0.25,
						},
					],
					filterControls() {
						return [
							{
								type: 'link',
								label: 'Version',
								fieldname: 'version',
								options: {
									doctype: 'Frappe Version',
								},
							},
							{
								type: 'link',
								label: 'Tag',
								fieldname: 'tags.tag',
								options: {
									doctype: 'Press Tag',
									filters: {
										doctype_name: 'Release Group',
									},
								},
							},
						];
					},
					route(row) {
						return {
							name: 'Release Group Detail',
							params: { name: row.name },
						};
					},
					primaryAction({ listResource: benches, documentResource: server }) {
						if (server?.doc?.status !== 'Active') return {};
						return {
							label: 'New Bench Group',
							slots: {
								prefix: icon('plus'),
							},
							onClick() {
								router.push({
									name: 'Server New Release Group',
									params: { server: server.doc.name },
								});
							},
						};
					},
				},
			},
			{
				label: 'Snapshots',
				icon: icon('camera'),
				condition: (server) => {
					if (!server?.doc) return true;
					return server?.doc?.provider === 'AWS EC2';
				},
				route: 'snapshots',
				type: 'list',
				list: {
					doctype: 'Server Snapshot',
					filters: (server) => {
						let filters = {
							app_server: server.doc?.name,
						};
						const snapshot_name = getQueryParam('name');
						if (snapshot_name) {
							filters.name = snapshot_name;
						}
						return filters;
					},
					filterControls() {
						const snapshot_name = getQueryParam('name');
						let filters = snapshot_name
							? [
									{
										type: 'text',
										label: 'Snapshot Name',
										fieldname: 'name',
									},
								]
							: [
									{
										type: 'select',
										label: 'Status',
										fieldname: 'status',
										options: [
											'',
											'Pending',
											'Processing',
											'Failure',
											'Completed',
											'Unavailable',
										],
									},
								];
						filters = filters.concat([
							{
								type: 'checkbox',
								label: 'Consistent',
								fieldname: 'consistent',
							},
						]);
						return filters;
					},
					searchField: getQueryParam('name') ? null : 'name',
					updateFilters({ name }) {
						setQueryParam('name', name);
					},
					autoReloadAfterUpdateFilterCallback: true,
					orderBy: 'creation desc',
					fields: [
						'name',
						'status',
						'creation',
						'consistent',
						'free',
						'expire_at',
						'total_size_gb',
					],
					columns: [
						{
							label: 'Snapshot',
							fieldname: 'name',
							width: 0.5,
							class: 'font-medium',
						},
						{
							label: 'Status',
							fieldname: 'status',
							type: 'Badge',
							width: 0.5,
							align: 'center',
						},
						{
							label: 'Size',
							fieldname: 'total_size_gb',
							width: 0.5,
							align: 'center',
							format(value) {
								if (!value) return '-';
								return `${value} GB`;
							},
						},
						{
							label: 'Consistent',
							fieldname: 'consistent',
							width: 0.3,
							type: 'Icon',
							align: 'center',
							Icon(value) {
								return value ? 'check' : 'x';
							},
						},
						{
							label: 'Free',
							fieldname: 'free',
							width: 0.3,
							type: 'Icon',
							Icon(value) {
								return value ? 'check' : 'x';
							},
						},
						{
							label: 'Locked',
							fieldname: 'locked',
							width: 0.3,
							type: 'Icon',
							align: 'center',
							Icon(value) {
								return value ? 'lock' : 'unlock';
							},
						},
						{
							label: 'Expire At',
							fieldname: 'expire_at',
							width: 1,
							align: 'center',
							format(value) {
								if (!value) return 'No Expiry';
								return date(value, 'llll');
							},
						},
						{
							label: 'Created At',
							fieldname: 'creation',
							width: 1,
							align: 'right',
							format(value) {
								return date(value, 'llll');
							},
						},
					],
					primaryAction({ documentResource: server, listResource: snapshots }) {
						if (server?.doc?.status === 'Archived') return;
						return {
							label: 'New Snapshot',
							slots: {
								prefix: icon('camera'),
							},
							onClick() {
								renderDialog(
									h(
										defineAsyncComponent(
											() =>
												import(
													'../components/server/ServerNewSnapshotDialog.vue'
												),
										),
										{
											server: server.name,
											onSnapshotCreated: () => {
												snapshots.reload();
											},
										},
									),
								);
							},
						};
					},
					rowActions({ row, documentResource: server }) {
						return [
							{
								label: 'View Details',
								onClick() {
									let ServerSnapshotDetailsDialog = defineAsyncComponent(
										() =>
											import(
												'../components/server/ServerSnapshotDetailsDialog.vue'
											),
									);
									renderDialog(
										h(ServerSnapshotDetailsDialog, {
											name: row.name,
										}),
									);
								},
							},
							{
								label: 'Recover Sites',
								condition: () => row.status === 'Completed',
								onClick() {
									let ServerSnapshotRecoverSitesDialog = defineAsyncComponent(
										() =>
											import(
												'../components/server/ServerSnapshotRecoverSitesDialog.vue'
											),
									);
									renderDialog(
										h(ServerSnapshotRecoverSitesDialog, {
											name: row.name,
										}),
									);
								},
							},
							{
								label: 'Lock',
								condition: () => row.status === 'Completed' && !row.locked,
								onClick() {
									confirmDialog({
										title: 'Lock Snapshot',
										message:
											'Are you sure you want to lock this snapshot? This will prevent the snapshot from being deleted accidentally.',
										primaryAction: {
											label: 'Lock',
											onClick: ({ hide }) => {
												toast.promise(
													server.lockSnapshot.submit(
														{
															snapshot_name: row.name,
														},
														{
															onSuccess() {
																hide();
															},
														},
													),
													{
														loading: 'Locking snapshot...',
														success: 'Snapshot will be locked shortly',
														error: (err) => {
															return err.messages?.length
																? err.messages.join('\n')
																: err.message || 'Failed to lock snapshot';
														},
													},
												);
											},
										},
									});
								},
							},
							{
								label: 'Unlock',
								condition: () => row.status === 'Completed' && row.locked,
								onClick() {
									confirmDialog({
										title: 'Unlock Snapshot',
										message:
											'Are you sure you want to unlock this snapshot ? After unlocking, the snapshot can be deleted by end-user.',
										primaryAction: {
											label: 'Unlock',
											onClick: ({ hide }) => {
												toast.promise(
													server.unlockSnapshot.submit(
														{
															snapshot_name: row.name,
														},
														{
															onSuccess() {
																hide();
															},
														},
													),
													{
														loading: 'Unlocking snapshot...',
														success: 'Snapshot will be unlocked shortly',
														error: (err) => {
															return err.messages?.length
																? err.messages.join('\n')
																: err.message || 'Failed to unlock snapshot';
														},
													},
												);
											},
										},
									});
								},
							},
							{
								label: 'Delete',
								condition: () => row.status === 'Completed',
								onClick() {
									confirmDialog({
										title: 'Delete Snapshot',
										message:
											'Are you sure you want to delete this snapshot? This will delete the snapshot and all associated recovered data.',
										primaryAction: {
											label: 'Delete',
											theme: 'red',
											onClick: ({ hide }) => {
												toast.promise(
													server.deleteSnapshot.submit(
														{
															snapshot_name: row.name,
														},
														{
															onSuccess() {
																hide();
															},
														},
													),
													{
														loading: 'Deleting snapshot...',
														success: 'Snapshot deleted successfully',
														error: (err) => {
															return err.messages?.length
																? err.messages.join('\n')
																: err.message || 'Failed to delete snapshot';
														},
													},
												);
											},
										},
									});
								},
							},
						];
					},
				},
			},
			getJobsTab('Server'),
			{
				label: 'Plays',
				icon: icon('play'),
				condition: (server) => {
					return server.doc?.status !== 'Archived';
				},
				childrenRoutes: ['Server Play'],
				route: 'plays',
				type: 'list',
				searchField: 'play',
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
									server.doc.replication_server,
								].filter(Boolean),
							},
						];
					},
					filters: (server) => {
						return {
							server: [
								'in',
								[
									server.doc.name,
									server.doc.database_server,
									server.doc.replication_server,
								].filter(Boolean),
							],
						};
					},
					route(row) {
						return {
							name: 'Server Play',
							params: { id: row.name },
						};
					},
					orderBy: 'creation desc',
					fields: ['server', 'end'],
					columns: [
						{
							label: 'Play',
							fieldname: 'play',
							width: 2,
						},
						{
							label: 'Status',
							fieldname: 'status',
							type: 'Badge',
							width: 0.5,
						},
						{
							label: 'Server',
							fieldname: 'server',
							width: 2,
						},
						{
							label: 'Duration',
							fieldname: 'duration',
							width: 0.5,
							format(value, row) {
								if (row.job_id === 0 || !row.end) return;
								return duration(value);
							},
						},
						{
							label: '',
							fieldname: 'creation',
							type: 'Timestamp',
							align: 'right',
						},
					],
				},
			},
			{
				label: 'Actions',
				icon: icon('sliders'),
				condition: (server) => {
					return server.doc?.status !== 'Archived';
				},
				route: 'actions',
				type: 'Component',
				component: ServerActions,
				props: (server) => {
					return { server: server.doc.name };
				},
			},
			{
				label: 'Auto Scale',
				icon: icon('maximize-2'),
				route: 'auto-scale',
				type: 'Component',
				condition: (server) => {
					if (!server?.doc) return true;
					return server?.doc?.secondary_server;
				},
				redirectTo: 'Triggered',
				childrenRoutes: ['Triggered', 'Scheduled'],
				nestedChildrenRoutes: [
					{
						name: 'Triggered',
						path: 'triggered',
						component: () =>
							import('../components/server/AutoScaleTriggered.vue'),
					},
					{
						name: 'Scheduled',
						path: 'scheduled',
						component: () =>
							import('../components/server/AutoScaleScheduled.vue'),
					},
				],
				component: defineAsyncComponent(
					() => import('../components/server/AutoScaleTabs.vue'),
				),
				props: (server) => {
					return {
						server: server.doc.name,
					};
				},
			},
			tagTab('Server'),
			{
				label: 'Activity',
				icon: icon('activity'),
				route: 'activity',
				type: 'list',
				condition: (server) => {
					return server.doc?.status !== 'Archived';
				},
				list: {
					doctype: 'Server Activity',
					filters: (server) => {
						return {
							document_name: [
								'in',
								[server.doc?.name, server.doc?.database_server],
							],
						};
					},
					orderBy: 'creation desc',
					fields: ['owner'],
					columns: [
						{
							label: 'Action',
							fieldname: 'action',
							format(value, row) {
								return `${row.action} by ${row.owner}`;
							},
						},
						{
							label: 'Server',
							fieldname: 'document_name',
						},
						{
							label: 'Description',
							fieldname: 'reason',
							class: 'text-gray-600',
						},
						{
							label: '',
							fieldname: 'creation',
							type: 'Timestamp',
							align: 'right',
						},
					],
					filterControls() {
						return [
							{
								type: 'select',
								label: 'Action',
								fieldname: 'action',
								class: !isMobile() ? 'w-52' : '',
								options: [
									'',
									'Created',
									'Reboot',
									'Volume',
									'Terminated',
									'Incident',
									'Disk Size Change',
								],
							},
						];
					},
				},
			},
		],
	},
	routes: [
		{
			name: 'Server Job',
			path: 'jobs/:id',
			component: () => import('../pages/JobPage.vue'),
		},
		{
			name: 'Server Play',
			path: 'plays/:id',
			component: () => import('../pages/PlayPage.vue'),
		},
		{
			name: 'Auto Scale Steps',
			path: 'auto-scale-steps/:id',
			component: () => import('../components/server/AutoScaleSteps.vue'),
		},
	],
};
