import { frappeRequest, LoadingIndicator } from 'frappe-ui';
import { defineAsyncComponent, h } from 'vue';
import { toast } from 'vue-sonner';
import AddDomainDialog from '../components/AddDomainDialog.vue';
import GenericDialog from '../components/GenericDialog.vue';
import ObjectList from '../components/ObjectList.vue';
import { getTeam } from '../data/team';
import router from '../router';
import { confirmDialog, icon, renderDialog } from '../utils/components';
import { bytes, duration, date } from '../utils/format';
import SiteActionCell from '../components/SiteActionCell.vue';
import { dayjsLocal } from '../utils/dayjs';
import { getRunningJobs } from '../utils/agentJob';
import SiteActions from '../components/SiteActions.vue';
import { tagTab } from './common/tags';

export default {
	doctype: 'Site',
	whitelistedMethods: {
		activate: 'activate',
		addDomain: 'add_domain',
		archive: 'archive',
		backup: 'backup',
		clearSiteCache: 'clear_site_cache',
		deactivate: 'deactivate',
		enableDatabaseAccess: 'enable_database_access',
		disableDatabaseAccess: 'disable_database_access',
		getDatabaseCredentials: 'get_database_credentials',
		disableReadWrite: 'disable_read_write',
		enableReadWrite: 'enable_read_write',
		installApp: 'install_app',
		uninstallApp: 'uninstall_app',
		migrate: 'migrate',
		moveToBench: 'move_to_bench',
		moveToGroup: 'move_to_group',
		loginAsAdmin: 'login_as_admin',
		reinstall: 'reinstall',
		removeDomain: 'remove_domain',
		restoreSite: 'restore_site',
		scheduleUpdate: 'schedule_update',
		setPlan: 'set_plan',
		updateConfig: 'update_config',
		deleteConfig: 'delete_config',
		sendTransferRequest: 'send_change_team_request',
		addTag: 'add_resource_tag',
		removeTag: 'remove_resource_tag'
	},
	list: {
		route: '/sites',
		title: 'Sites',
		fields: [
			'plan.plan_title as plan_title',
			'plan.price_usd as price_usd',
			'plan.price_inr as price_inr',
			'group.title as group_title',
			'group.public as group_public',
			'group.version as version',
			'cluster.image as cluster_image',
			'cluster.title as cluster_title',
			'trial_end_date'
		],
		orderBy: 'creation desc',
		columns: [
			{ label: 'Site', fieldname: 'name', width: 1.5 },
			{ label: 'Status', fieldname: 'status', type: 'Badge', width: 0.8 },
			{
				label: 'Plan',
				fieldname: 'plan',
				width: 1,
				format(value, row) {
					if (row.trial_end_date) {
						let trialEndDate = dayjsLocal(row.trial_end_date);
						if (trialEndDate.isAfter(dayjsLocal())) {
							return 'Trial';
						}
					}
					let $team = getTeam();
					if (row.price_usd > 0) {
						let india = $team.doc.country == 'India';
						let currencySymbol = $team.doc.currency == 'INR' ? '₹' : '$';
						return `${currencySymbol}${
							india ? row.price_inr : row.price_usd
						} /mo`;
					}
					return row.plan_title;
				}
			},
			{
				label: 'Cluster',
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
			},
			{
				label: 'Bench',
				fieldname: 'group',
				width: 1,
				format(value, row) {
					return row.group_public ? 'Shared' : row.group_title || value;
				}
			},
			{
				label: 'Version',
				fieldname: 'version',
				width: 1,
				class: 'text-gray-600'
			}
		],
		primaryAction({ listResource: sites }) {
			return {
				label: 'New Site',
				variant: 'solid',
				slots: {
					prefix: icon('plus')
				},
				onClick() {
					router.push({ name: 'NewSite' });
				}
			};
		}
	},
	detail: {
		titleField: 'name',
		route: '/sites/:name',
		statusBadge({ documentResource: site }) {
			return { label: site.doc.status };
		},
		breadcrumbs({ items, documentResource: site }) {
			if (site.doc?.group_public) {
				return items;
			}
			return [
				{
					label: site.doc?.group_title,
					route: `/benches/${site.doc?.group}`
				},
				items[1]
			];
		},
		tabs: [
			{
				label: 'Overview',
				icon: icon('home'),
				route: 'overview',
				type: 'Component',
				component: defineAsyncComponent(() =>
					import('../components/SiteOverview.vue')
				),
				props: site => {
					return { site: site.doc.name };
				}
			},
			{
				label: 'Analytics',
				icon: icon('bar-chart-2'),
				route: 'analytics',
				type: 'Component',
				component: defineAsyncComponent(() =>
					import('../../src/views/site/SiteCharts.vue')
				),
				props: site => {
					return { site: site.doc };
				}
			},
			{
				label: 'Apps',
				icon: icon('grid'),
				route: 'apps',
				type: 'list',
				list: {
					doctype: 'Site App',
					filters: site => {
						return { parenttype: 'Site', parent: site.doc.name };
					},
					columns: [
						{
							label: 'App',
							fieldname: 'app',
							width: 1
						},
						{
							label: 'Branch',
							fieldname: 'branch',
							type: 'Badge',
							width: 1,
							link: (value, row) => {
								return `${row.repository_url}/tree/${value}`;
							}
						},
						{
							label: 'Commit',
							fieldname: 'hash',
							type: 'Badge',
							width: 1,
							link: (value, row) => {
								return `${row.repository_url}/commit/${value}`;
							},
							format(value) {
								return value.slice(0, 7);
							}
						},
						{
							label: 'Commit Message',
							fieldname: 'commit_message',
							width: '34rem'
						}
					],
					primaryAction({ listResource: apps, documentResource: site }) {
						return {
							label: 'Install App',
							slots: {
								prefix: icon('plus')
							},
							onClick() {
								renderDialog(
									h(
										GenericDialog,
										{
											options: {
												title: 'Install app on your site',
												size: '4xl'
											}
										},
										{
											default: () =>
												h(ObjectList, {
													options: {
														label: 'App',
														fieldname: 'app',
														fieldtype: 'ListSelection',
														columns: [
															{
																label: 'Title',
																fieldname: 'title',
																class: 'font-medium',
																width: 2
															},
															{
																label: 'Repo',
																fieldname: 'repository_owner',
																class: 'text-gray-600'
															},
															{
																label: 'Branch',
																fieldname: 'branch',
																class: 'text-gray-600'
															},
															{
																label: '',
																fieldname: '',
																align: 'right',
																type: 'Button',
																width: '5rem',
																Button({ row }) {
																	return {
																		label: 'Install',
																		onClick() {
																			if (site.installApp.loading) return;
																			toast.promise(
																				site.installApp.submit({
																					app: row.app
																				}),
																				{
																					loading: 'Installing app...',
																					success: () =>
																						'App will be installed shortly',
																					error: e => {
																						return e.messages.length
																							? e.messages.join('\n')
																							: e.message;
																					}
																				}
																			);
																		}
																	};
																}
															}
														],
														resource() {
															return {
																url: 'press.api.site.available_apps',
																params: {
																	name: site.doc.name
																},
																auto: true
															};
														}
													}
												})
										}
									)
								);
							}
						};
					},
					rowActions({ row, listResource: apps, documentResource: site }) {
						let $team = getTeam();

						return [
							{
								label: 'View in Desk',
								condition: () => $team.doc.is_desk_user,
								onClick() {
									window.open(`/app/app-source/${row.name}`, '_blank');
								}
							},
							{
								label: 'Change Plan',
								condition: () => row.plan_info && row.plans.length > 1,
								onClick() {
									let SiteAppPlanChangeDialog = defineAsyncComponent(() =>
										import('../components/site/SiteAppPlanChangeDialog.vue')
									);
									renderDialog(
										h(SiteAppPlanChangeDialog, {
											app: row,
											currentPlan: row.plans.find(
												plan => plan.plan === row.plan_info.name
											),
											onPlanChanged() {
												apps.reload();
											}
										})
									);
								}
							},
							{
								label: 'Uninstall',
								condition: () => row.app !== 'frappe',
								onClick() {
									confirmDialog({
										title: `Uninstall App`,
										message: `Are you sure you want to uninstall the app <b>${row.title}</b> from the site <b>${site.doc.name}</b>?<br>
										All doctypes and modules related to this app will be removed.`,
										onSuccess({ hide }) {
											if (site.uninstallApp.loading) return;
											toast.promise(
												site.uninstallApp.submit(
													{
														app: row.app
													},
													{
														onSuccess: () => {
															hide();
															apps.reload();
														}
													}
												),
												{
													loading: 'Uninstalling app...',
													success: () => 'App uninstalled successfully',
													error: e => {
														return e.messages.length
															? e.messages.join('\n')
															: e.message;
													}
												}
											);
										}
									});
								}
							}
						];
					}
				}
			},
			{
				label: 'Domains',
				icon: icon('external-link'),
				route: 'domains',
				type: 'list',
				list: {
					doctype: 'Site Domain',
					filters: site => {
						return { site: site.doc.name };
					},
					columns: [
						{
							label: 'Domain',
							fieldname: 'domain'
						},
						{
							label: 'Status',
							fieldname: 'status',
							type: 'Badge'
						},
						{
							label: 'Primary',
							fieldname: 'primary',
							type: 'Icon',
							Icon(value) {
								return value ? 'check' : '';
							}
						},
						{
							label: 'DNS Type',
							fieldname: 'dns_type',
							type: 'Badge'
						}
					],
					primaryAction({ listResource: domains, documentResource: site }) {
						return {
							label: 'Add Domain',
							slots: {
								prefix: icon('plus')
							},
							onClick() {
								renderDialog(
									h(AddDomainDialog, {
										site: site.doc,
										onDomainAdded() {
											domains.reload();
										}
									})
								);
							}
						};
					},
					rowActions({ row, listResource: domains, documentResource: site }) {
						if (row.domain === site.doc.name) return;
						return [
							{
								label: 'Remove',
								onClick() {
									if (site.removeDomain.loading) return;
									toast.promise(
										site.removeDomain.submit({
											domain: row.domain
										}),
										{
											loading: 'Removing domain...',
											success: () => 'Domain removed',
											error: e => {
												return e.messages.length
													? e.messages.join('\n')
													: e.message;
											}
										}
									);
								}
							}
						];
					}
				}
			},
			{
				label: 'Backups',
				icon: icon('archive'),
				route: 'backups',
				type: 'list',
				list: {
					doctype: 'Site Backup',
					filters: site => {
						return {
							site: site.doc.name,
							files_availability: 'Available',
							status: ['in', ['Pending', 'Running', 'Success']]
						};
					},
					orderBy: 'creation desc',
					fields: [
						'status',
						'database_url',
						'public_url',
						'private_url',
						'config_file_url',
						'site'
					],
					columns: [
						{
							label: 'Timestamp',
							fieldname: 'creation',
							width: 1,
							format(value) {
								return `Backup on ${date(value, 'llll')}`;
							}
						},

						{
							label: 'Database',
							fieldname: 'database_size',
							width: 0.5,
							format(value) {
								return value ? bytes(value) : '';
							}
						},
						{
							label: 'Public Files',
							fieldname: 'public_size',
							width: 0.5,
							format(value) {
								return value ? bytes(value) : '';
							}
						},
						{
							label: 'Private Files',
							fieldname: 'private_size',
							width: 0.5,
							format(value) {
								return value ? bytes(value) : '';
							}
						},
						{
							label: 'Backup with files',
							fieldname: 'with_files',
							type: 'Icon',
							width: 0.5,
							Icon(value) {
								return value ? 'check' : '';
							}
						},
						{
							label: 'Offsite Backup',
							fieldname: 'offsite',
							width: 0.5,
							type: 'Icon',
							Icon(value) {
								return value ? 'check' : '';
							}
						}
					],
					rowActions({ row }) {
						if (row.status != 'Success') return;

						async function downloadBackup(backup, file) {
							// file: database, public, or private
							let link = backup.offsite
								? await frappeRequest('press.api.site.get_backup_link', {
										name: backup.site,
										backup: backup.name,
										file
								  })
								: backup[file + '_url'];
							window.open(link);
						}

						return [
							{
								label: 'Download Database',
								onClick() {
									return downloadBackup(row, 'database');
								}
							},
							{
								label: 'Download Public',
								onClick() {
									return downloadBackup(row, 'public');
								},
								condition: () => row.public_url
							},
							{
								label: 'Download Private',
								onClick() {
									return downloadBackup(row, 'private');
								},
								condition: () => row.private_url
							},
							{
								label: 'Download Config',
								onClick() {
									return downloadBackup(row, 'config_file');
								},
								condition: () => row.config_file_url
							}
						];
					},
					primaryAction({ listResource: backups, documentResource: site }) {
						return {
							label: 'Schedule Backup',
							slots: {
								prefix: icon('upload-cloud')
							},
							loading: site.backup.loading,
							onClick() {
								return site.backup.submit(
									{
										with_files: true
									},
									{
										onError(e) {
											showErrorToast(e);
										},
										onSuccess() {
											backups.reload();
											toast.success('Backup scheduled');
										}
									}
								);
							}
						};
					}
				}
			},
			{
				label: 'Site Config',
				icon: icon('settings'),
				route: 'site-config',
				type: 'list',
				list: {
					doctype: 'Site Config',
					filters: site => {
						return { parent: site.doc.name, parenttype: 'Site' };
					},
					fields: ['name'],
					pageLength: 999,
					orderBy: 'creation desc',
					columns: [
						{
							label: 'Config Name',
							fieldname: 'key',
							width: 1,
							format(value, row) {
								if (row.title) {
									return `${row.title} (${row.key})`;
								}
								return row.key;
							}
						},
						{
							label: 'Config Value',
							fieldname: 'value',
							class: 'font-mono',
							width: 2
						},
						{
							label: 'Type',
							fieldname: 'type',
							type: 'Badge',
							width: '100px'
						}
					],
					primaryAction({ listResource: configs, documentResource: site }) {
						return {
							label: 'Add Config',
							slots: {
								prefix: icon('plus')
							},
							onClick() {
								let ConfigEditorDialog = defineAsyncComponent(() =>
									import('../components/ConfigEditorDialog.vue')
								);
								renderDialog(
									h(ConfigEditorDialog, {
										site: site.doc.name,
										onSuccess() {
											configs.reload();
										}
									})
								);
							}
						};
					},
					secondaryAction({ listResource: configs }) {
						return {
							label: 'Preview',
							slots: {
								prefix: icon('eye')
							},
							onClick() {
								let ConfigPreviewDialog = defineAsyncComponent(() =>
									import('../components/ConfigPreviewDialog.vue')
								);
								renderDialog(
									h(ConfigPreviewDialog, {
										configs: configs.data
									})
								);
							}
						};
					},
					rowActions({ row, listResource: configs, documentResource: site }) {
						return [
							{
								label: 'Edit',
								onClick() {
									let ConfigEditorDialog = defineAsyncComponent(() =>
										import('../components/ConfigEditorDialog.vue')
									);
									renderDialog(
										h(ConfigEditorDialog, {
											site: site.doc.name,
											config: row,
											onSuccess() {
												configs.reload();
											}
										})
									);
								}
							},
							{
								label: 'Delete',
								onClick() {
									confirmDialog({
										title: 'Delete Config',
										message: `Are you sure you want to delete the config <b>${row.key}</b>?`,
										onSuccess({ hide }) {
											if (site.deleteConfig.loading) return;
											toast.promise(
												site.deleteConfig.submit(
													{ key: row.key },
													{
														onSuccess: () => {
															configs.reload();
															hide();
														}
													}
												),
												{
													loading: 'Deleting config...',
													success: () => `Config ${row.key} removed`,
													error: e => {
														return e.messages.length
															? e.messages.join('\n')
															: e.message;
													}
												}
											);
										}
									});
								}
							}
						];
					}
				}
			},
			{
				label: 'Actions',
				icon: icon('activity'),
				route: 'actions',
				type: 'Component',
				component: SiteActions,
				props: site => {
					return { site: site.doc.name };
				}
			},
			{
				label: 'Jobs',
				icon: icon('truck'),
				childrenRoutes: ['Site Job'],
				route: 'jobs',
				type: 'list',
				list: {
					doctype: 'Agent Job',
					filters: site => {
						return { site: site.doc.name };
					},
					route(row) {
						return {
							name: 'Site Job',
							params: { id: row.name, site: row.site }
						};
					},
					orderBy: 'creation desc',
					fields: ['site', 'end'],
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
							label: 'Created By',
							fieldname: 'owner',
							width: 1
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
				label: 'Activity',
				icon: icon('activity'),
				route: 'activity',
				type: 'list',
				list: {
					doctype: 'Site Activity',
					filters: site => {
						return { site: site.doc.name };
					},
					fields: ['owner'],
					orderBy: 'creation desc',
					columns: [
						{
							label: 'Action',
							fieldname: 'action',
							format(value, row) {
								let action = row.action;
								if (action == 'Create') {
									action = 'Site created';
								}
								return `${action} by ${row.owner}`;
							}
						},
						{
							label: 'Reason',
							fieldname: 'reason',
							class: 'text-gray-600'
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
		],
		actions(context) {
			let { documentResource: site } = context;
			let $team = getTeam();
			let runningJobs = getRunningJobs({ site: site.doc.name });

			return [
				{
					label: 'Jobs in progress',
					slots: {
						prefix: () => h(LoadingIndicator, { class: 'w-4 h-4' })
					},
					condition() {
						return (
							runningJobs.filter(job =>
								['Pending', 'Running'].includes(job.status)
							).length > 0
						);
					},
					onClick() {
						router.push({
							name: 'Site Detail Jobs',
							params: { name: site.name }
						});
					}
				},
				{
					label: 'Update Available',
					variant: 'solid',
					slots: {
						prefix: icon('alert-circle')
					},
					condition() {
						return (
							site.doc.update_information?.update_available &&
							['Active', 'Inactive', 'Suspended', 'Broken'].includes(
								site.doc.status
							)
						);
					},

					onClick() {
						let SiteUpdateDialog = defineAsyncComponent(() =>
							import('../components/SiteUpdateDialog.vue')
						);
						renderDialog(h(SiteUpdateDialog, { site: site.doc.name }));
					}
				},
				{
					label: 'Visit Site',
					slots: {
						prefix: icon('external-link')
					},
					condition: () => site.doc.status === 'Active',
					onClick() {
						window.open(`https://${site.name}`, '_blank');
					}
				},
				{
					label: 'Options',
					button: {
						label: 'Options',
						slots: {
							icon: icon('more-horizontal')
						}
					},
					context,
					options: [
						{
							label: 'View in Desk',
							icon: 'external-link',
							condition: () => $team.doc.is_desk_user,
							onClick: () => {
								window.open(
									`${window.location.protocol}//${window.location.host}/app/site/${site.name}`,
									'_blank'
								);
							}
						},
						{
							label: 'Manage Bench',
							icon: 'tool',
							condition: () => site.doc?.group,
							onClick: () => {
								router.push(`/benches/${site.doc?.group}`);
							}
						},
						{
							label: 'Login As Administrator',
							icon: 'external-link',
							condition: () => site.doc.status === 'Active',
							onClick: () => {
								confirmDialog({
									title: 'Login as Administrator',
									fields: [
										{
											label: 'Reason',
											type: 'textarea',
											fieldname: 'reason'
										}
									],
									onSuccess: ({ hide, values }) => {
										if (!values.reason && $team.name != site.doc.team) {
											throw new Error('Reason is required');
										}
										return site.loginAsAdmin
											.submit({ reason: values.reason })
											.then(result => {
												let url = result;
												window.open(url, '_blank');
												hide();
											});
									}
								});
							}
						}
					]
				}
			];
		}
	},
	routes: [
		{
			name: 'Site Job',
			path: 'job/:id',
			component: () => import('../pages/JobPage.vue')
		}
	]
};
