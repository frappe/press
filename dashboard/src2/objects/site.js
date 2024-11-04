import {
	createListResource,
	createResource,
	LoadingIndicator
} from 'frappe-ui';
import { defineAsyncComponent, h } from 'vue';
import { toast } from 'vue-sonner';
import AddDomainDialog from '../components/AddDomainDialog.vue';
import GenericDialog from '../components/GenericDialog.vue';
import ObjectList from '../components/ObjectList.vue';
import SiteActions from '../components/SiteActions.vue';
import { getTeam, switchToTeam } from '../data/team';
import router from '../router';
import { getRunningJobs } from '../utils/agentJob';
import { confirmDialog, icon, renderDialog } from '../utils/components';
import dayjs from '../utils/dayjs';
import { bytes, date, userCurrency } from '../utils/format';
import { getDocResource } from '../utils/resource';
import { trialDays } from '../utils/site';
import { clusterOptions, getUpsellBanner } from './common';
import { getAppsTab } from './common/apps';
import { isMobile } from '../utils/device';

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
		loginAsTeam: 'login_as_team',
		isSetupWizardComplete: 'is_setup_wizard_complete',
		reinstall: 'reinstall',
		removeDomain: 'remove_domain',
		redirectToPrimary: 'set_redirect',
		removeRedirect: 'unset_redirect',
		setPrimaryDomain: 'set_host_name',
		restoreSite: 'restore_site',
		restoreSiteFromFiles: 'restore_site_from_files',
		scheduleUpdate: 'schedule_update',
		editScheduledUpdate: 'edit_scheduled_update',
		cancelUpdate: 'cancel_scheduled_update',
		setPlan: 'set_plan',
		updateConfig: 'update_config',
		deleteConfig: 'delete_config',
		sendTransferRequest: 'send_change_team_request',
		addTag: 'add_resource_tag',
		removeTag: 'remove_resource_tag',
		getBackupDownloadLink: 'get_backup_download_link',
		fetchDatabaseTableSchemas: 'fetch_database_table_schemas'
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
			'group.team as group_team',
			'group.version as version',
			'cluster.image as cluster_image',
			'cluster.title as cluster_title',
			'trial_end_date'
		],
		orderBy: 'creation desc',
		searchField: 'host_name',
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
					type: 'select',
					label: 'Region',
					fieldname: 'cluster',
					options: clusterOptions
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
			{ label: 'Status', fieldname: 'status', type: 'Badge', width: 0.7 },
			{
				label: 'Plan',
				fieldname: 'plan',
				width: 0.85,
				format(value, row) {
					if (row.trial_end_date) {
						return trialDays(row.trial_end_date);
					}
					const $team = getTeam();
					if (row.price_usd > 0) {
						const india = $team.doc.currency === 'INR';
						const formattedValue = userCurrency(
							india ? row.price_inr : row.price_usd,
							0
						);
						return `${formattedValue}/mo`;
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
			},
			{
				label: 'Bench Group',
				fieldname: 'group',
				width: '15rem',
				format(value, row) {
					return row.group_public ? 'Shared' : row.group_title || value;
				}
			},
			{
				label: 'Version',
				fieldname: 'version',
				width: 0.5
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
					router.push({ name: 'New Site' });
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
			let breadcrumbs = [];
			let $team = getTeam();
			let siteCrumb = {
				label: site.doc.host_name || site.doc?.name,
				route: `/sites/${site.doc?.name}`
			};

			if (
				(site.doc.server_team == $team.doc?.name &&
					site.doc.group_team == $team.doc?.name) ||
				$team.doc?.is_desk_user
			) {
				breadcrumbs.push({
					label: site.doc?.server_title || site.doc?.server,
					route: `/servers/${site.doc?.server}`
				});
			}
			if (
				site.doc.group_team == $team.doc?.name ||
				$team.doc?.is_desk_user ||
				$team.doc?.is_support_agent
			) {
				breadcrumbs.push(
					{
						label: site.doc?.group_title,
						route: `/groups/${site.doc?.group}`
					},
					siteCrumb
				);
			} else {
				breadcrumbs.push(...items.slice(0, -1), siteCrumb);
			}
			return breadcrumbs;
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
					return { site: site.doc?.name };
				}
			},
			{
				label: 'Insights',
				icon: icon('bar-chart-2'),
				route: 'insights',
				type: 'Component',
				redirectTo: 'Site Analytics',
				childrenRoutes: [
					'Site Jobs',
					'Site Job',
					'Site Logs',
					'Site Log',
					'Site Analytics',
					'Site Performance Reports',
					'Site Performance Request Logs',
					'Site Performance Slow Queries',
					'Site Performance Binary Logs',
					'Site Performance Process List',
					'Site Performance Request Log',
					'Site Performance Deadlock Report'
				],
				nestedChildrenRoutes: [
					{
						name: 'Site Analytics',
						path: 'analytics',
						component: () => import('../components/site/SiteAnalytics.vue')
					},
					{
						name: 'Site Jobs',
						path: 'jobs',
						component: () => import('../components/site/SiteJobs.vue')
					},
					{
						name: 'Site Job',
						path: 'jobs/:id',
						component: () => import('../pages/JobPage.vue')
					},
					{
						name: 'Site Logs',
						path: 'logs/:type?',
						component: () => import('../components/site/SiteLogs.vue')
					},
					{
						name: 'Site Log',
						path: 'logs/view/:logName',
						component: () => import('../pages/LogPage.vue')
					},
					{
						name: 'Site Performance Reports',
						path: 'performance',
						component: () =>
							import('../components/site/performance/SitePerformance.vue')
					},
					{
						name: 'Site Performance Slow Queries',
						path: 'performance/slow-queries',
						component: () =>
							import('../components/site/performance/SiteSlowQueries.vue')
					},
					{
						name: 'Site Performance Binary Logs',
						path: 'performance/binary-logs',
						component: () =>
							import('../components/site/performance/SiteBinaryLogs.vue')
					},
					{
						name: 'Site Performance Process List',
						path: 'performance/process-list',
						component: () =>
							import('../components/site/performance/SiteProcessList.vue')
					},
					{
						name: 'Site Performance Request Logs',
						path: 'performance/request-log',
						component: () =>
							import('../components/site/performance/SiteRequestLogs.vue')
					},
					{
						name: 'Site Performance Deadlock Report',
						path: 'performance/deadlock-report',
						component: () =>
							import('../components/site/performance/SiteDeadlockReport.vue')
					}
				],
				component: defineAsyncComponent(() =>
					import('../components/site/SiteInsights.vue')
				),
				props: site => {
					return { site: site.doc?.name };
				}
			},
			getAppsTab(true),
			{
				label: 'Domains',
				icon: icon('external-link'),
				route: 'domains',
				type: 'list',
				list: {
					doctype: 'Site Domain',
					fields: ['redirect_to_primary'],
					filters: site => {
						return { site: site.doc?.name };
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
					banner({ documentResource: site }) {
						if (site.doc.broken_domain_error) {
							return {
								title:
									'There was an error fetching an https certificate for your domain.',
								type: 'error',
								button: {
									label: 'View Error',
									variant: 'outline',
									onClick() {
										renderDialog(
											h(
												GenericDialog,
												{
													options: {
														title: 'Error fetching certificate',
														size: 'xl'
													}
												},
												{
													default: () => {
														return h('pre', {
															class:
																'whitespace-pre-wrap text-sm rounded border-2 p-3 border-gray-200 bg-gray-100',
															innerHTML: site.doc.broken_domain_error
														});
													}
												}
											)
										);
									}
								}
							};
						} else {
							return null;
						}
					},
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
						return [
							{
								label: 'Remove',
								condition: () => row.domain !== site.doc?.name,
								onClick() {
									confirmDialog({
										title: `Remove Domain`,
										message: `Are you sure you want to remove the domain <b>${row.domain}</b> from the site <b>${site.doc?.name}</b>?`,
										onSuccess({ hide }) {
											if (site.removeDomain.loading) return;
											toast.promise(
												site.removeDomain.submit({
													domain: row.domain
												}),
												{
													loading: 'Removing domain...',
													success: () => {
														hide();
														return 'Domain removed';
													},
													error: e => {
														return e.messages?.length
															? e.messages.join('\n')
															: e.message;
													}
												}
											);
										}
									});
								}
							},
							{
								label: 'Set Primary',
								condition: () => !row.primary && row.status === 'Active',
								onClick() {
									confirmDialog({
										title: `Set Primary Domain`,
										message: `Are you sure you want to set the domain <b>${row.domain}</b> as the primary domain for the site <b>${site.doc?.name}</b>?`,
										onSuccess({ hide }) {
											if (site.setPrimaryDomain.loading) return;
											toast.promise(
												site.setPrimaryDomain.submit({
													domain: row.domain
												}),
												{
													loading: 'Setting primary domain...',
													success: () => {
														hide();
														return 'Primary domain set';
													},
													error: e => {
														return e.messages?.length
															? e.messages.join('\n')
															: e.message;
													}
												}
											);
										}
									});
								}
							},
							{
								label: 'Redirect to Primary',
								condition: () =>
									!row.primary &&
									!row.redirect_to_primary &&
									row.status === 'Active',
								onClick() {
									confirmDialog({
										title: `Redirect Domain`,
										message: `Are you sure you want to redirect the domain <b>${row.domain}</b> to the primary domain of the site <b>${site.doc?.name}</b>?`,
										onSuccess({ hide }) {
											if (site.redirectToPrimary.loading) return;
											toast.promise(
												site.redirectToPrimary.submit({
													domain: row.domain
												}),
												{
													loading: 'Redirecting domain...',
													success: () => {
														hide();
														return 'Domain redirected';
													},
													error: e => {
														return e.messages?.length
															? e.messages.join('\n')
															: e.message;
													}
												}
											);
										}
									});
								}
							},
							{
								label: 'Remove Redirect',
								condition: () =>
									!row.primary &&
									row.redirect_to_primary &&
									row.status === 'Active',
								onClick() {
									confirmDialog({
										title: `Remove Redirect`,
										message: `Are you sure you want to remove the redirect from the domain <b>${row.domain}</b> to the primary domain of the site <b>${site.doc?.name}</b>?`,
										onSuccess({ hide }) {
											if (site.removeRedirect.loading) return;
											toast.promise(
												site.removeRedirect.submit({
													domain: row.domain
												}),
												{
													loading: 'Removing redirect...',
													success: () => {
														hide();
														return 'Redirect removed';
													},
													error: e => {
														return e.messages?.length
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
				label: 'Backups',
				icon: icon('archive'),
				route: 'backups',
				type: 'list',
				list: {
					doctype: 'Site Backup',
					filters: site => {
						return {
							site: site.doc?.name,
							files_availability: 'Available',
							status: ['in', ['Pending', 'Running', 'Success']]
						};
					},
					orderBy: 'creation desc',
					fields: [
						'job',
						'status',
						'database_url',
						'public_url',
						'private_url',
						'config_file_url',
						'site',
						'remote_database_file',
						'remote_public_file',
						'remote_private_file',
						'remote_config_file'
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
					filterControls() {
						return [
							{
								type: 'checkbox',
								label: 'Offsite Backups',
								fieldname: 'offsite'
							}
						];
					},
					rowActions({ row, documentResource: site }) {
						if (row.status != 'Success') return;

						function getFileName(file) {
							if (file == 'database') return 'database';
							if (file == 'public') return 'public files';
							if (file == 'private') return 'private files';
							if (file == 'config') return 'config file';
						}

						function confirmDownload(backup, file) {
							confirmDialog({
								title: 'Download Backup',
								message: `You will be downloading the ${getFileName(
									file
								)} backup of the site <b>${
									site.doc?.host_name || site.doc?.name
								}</b> that was created on ${date(backup.creation, 'llll')}.${
									!backup.offsite
										? '<br><br><div class="p-2 bg-gray-100 border-gray-200 rounded">You have to be logged in as a <b>System Manager</b> <em>in your site</em> to download the backup.<div>'
										: ''
								}`,
								onSuccess() {
									downloadBackup(backup, file);
								}
							});
						}

						async function downloadBackup(backup, file) {
							// file: database, public, or private
							if (backup.offsite) {
								site.getBackupDownloadLink.submit(
									{ backup: backup.name, file },
									{
										onSuccess(r) {
											// TODO: fix this in documentResource, it should return message directly
											if (r.message) {
												window.open(r.message);
											}
										}
									}
								);
							} else {
								const url =
									file == 'config'
										? backup.config_file_url
										: backup[file + '_url'];

								const domainRegex = /^(https?:\/\/)?([^/]+)\/?/;
								const newUrl = url.replace(
									domainRegex,
									`$1${site.doc.host_name}/`
								);
								window.open(newUrl);
							}
						}

						return [
							{
								group: 'Details',
								items: [
									{
										label: 'View Job',
										onClick() {
											router.push({
												name: 'Site Job',
												params: { name: site.name, id: row.job }
											});
										}
									}
								]
							},
							{
								group: 'Download',
								items: [
									{
										label: 'Download Database',
										onClick() {
											return confirmDownload(row, 'database');
										}
									},
									{
										label: 'Download Public',
										onClick() {
											return confirmDownload(row, 'public');
										},
										condition: () => row.public_url
									},
									{
										label: 'Download Private',
										onClick() {
											return confirmDownload(row, 'private');
										},
										condition: () => row.private_url
									},
									{
										label: 'Download Config',
										onClick() {
											return confirmDownload(row, 'config');
										},
										condition: () => row.config_file_url
									}
								]
							},
							{
								group: 'Restore',
								condition: () => row.offsite,
								items: [
									{
										label: 'Restore Backup',
										onClick() {
											confirmDialog({
												title: 'Restore Backup',
												message: `Are you sure you want to restore your site to this offsite backup from <b>${dayjs(
													row.creation
												).format('lll')}</b> ?`,
												onSuccess({ hide }) {
													toast.promise(
														site.restoreSiteFromFiles.submit({
															files: {
																database: row.remote_database_file,
																public: row.remote_public_file,
																private: row.remote_private_file,
																config: row.remote_config_file
															}
														}),
														{
															loading: 'Scheduling backup restore...',
															success: jobId => {
																hide();
																router.push({
																	name: 'Site Job',
																	params: {
																		name: site.name,
																		id: jobId
																	}
																});
																return 'Backup restore scheduled successfully.';
															},
															error: e => {
																return e.messages?.length
																	? e.messages.join('\n')
																	: e.message;
															}
														}
													);
												}
											});
										}
									},
									{
										label: 'Restore Backup on another Site',
										onClick() {
											let SelectSiteForRestore = defineAsyncComponent(() =>
												import('../components/site/SelectSiteForRestore.vue')
											);
											renderDialog(
												h(SelectSiteForRestore, {
													site: site.name,
													onRestore(siteName) {
														const restoreSite = createResource({
															url: 'press.api.site.restore'
														});

														return toast.promise(
															restoreSite.submit({
																name: siteName,
																files: {
																	database: row.remote_database_file,
																	public: row.remote_public_file,
																	private: row.remote_private_file,
																	config: row.remote_config_file
																}
															}),
															{
																loading: 'Scheduling backup restore...',
																success: jobId => {
																	router.push({
																		name: 'Site Job',
																		params: { name: siteName, id: jobId }
																	});
																	return 'Backup restore scheduled successfully.';
																},
																error: e => {
																	return e.messages?.length
																		? e.messages.join('\n')
																		: e.message;
																}
															}
														);
													}
												})
											);
										}
									}
								]
							}
						].filter(d => (d.condition ? d.condition() : true));
					},
					primaryAction({ listResource: backups, documentResource: site }) {
						return {
							label: 'Schedule Backup',
							slots: {
								prefix: icon('upload-cloud')
							},
							loading: site.backup.loading,
							onClick() {
								confirmDialog({
									title: 'Schedule Backup',
									message:
										'Are you sure you want to schedule a backup? This will create an onsite backup.',
									onSuccess({ hide }) {
										toast.promise(
											site.backup.submit({
												with_files: true
											}),
											{
												loading: 'Scheduling backup...',
												success: () => {
													hide();
													router.push({
														name: 'Site Jobs',
														params: { name: site.name }
													});
													return 'Backup scheduled successfully.';
												},
												error: e => {
													return e.messages?.length
														? e.messages.join('\n')
														: e.message;
												}
											}
										);
									}
								});
							}
						};
					},
					banner({ documentResource: site }) {
						const bannerTitle =
							'Your site is currently on a shared bench group. Upgrade plan for offsite backups and <a href="https://frappecloud.com/shared-hosting#benches" class="underline" target="_blank">more</a>.';

						return getUpsellBanner(site, bannerTitle);
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
						return { parent: site.doc?.name, parenttype: 'Site' };
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
										site: site.doc?.name,
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
											site: site.doc?.name,
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
														return e.messages?.length
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
				icon: icon('sliders'),
				route: 'actions',
				type: 'Component',
				component: SiteActions,
				props: site => {
					return { site: site.doc?.name };
				}
			},
			{
				label: 'Updates',
				icon: icon('arrow-up-circle'),
				route: 'updates',
				type: 'list',
				list: {
					doctype: 'Site Update',
					filters: site => {
						return { site: site.doc?.name };
					},
					orderBy: 'creation',
					fields: ['difference', 'update_job.end as updated_on', 'update_job'],
					columns: [
						{
							label: 'Type',
							fieldname: 'deploy_type',
							width: 0.3
						},
						{
							label: 'Status',
							fieldname: 'status',
							type: 'Badge',
							width: 0.5
						},
						{
							label: 'Created By',
							fieldname: 'owner'
						},
						{
							label: 'Scheduled At',
							fieldname: 'scheduled_time',
							format(value) {
								return date(value, 'lll');
							}
						},
						{
							label: 'Updated On',
							fieldname: 'updated_on',
							format(value) {
								return date(value, 'lll');
							}
						}
					],
					rowActions({ row, documentResource: site }) {
						return [
							{
								label: 'Edit',
								condition: () => row.status === 'Scheduled',
								onClick() {
									let SiteUpdateDialog = defineAsyncComponent(() =>
										import('../components/SiteUpdateDialog.vue')
									);
									renderDialog(
										h(SiteUpdateDialog, {
											site: site.doc?.name,
											existingUpdate: row.name
										})
									);
								}
							},
							{
								label: 'Cancel',
								condition: () => row.status === 'Scheduled',
								onClick() {
									confirmDialog({
										title: 'Cancel Update',
										message: `Are you sure you want to cancel the scheduled update?`,
										onSuccess({ hide }) {
											if (site.cancelUpdate.loading) return;
											toast.promise(
												site.cancelUpdate.submit({ site_update: row.name }),
												{
													loading: 'Cancelling update...',
													success: () => {
														hide();
														site.reload();
														return 'Update cancelled';
													},
													error: e => {
														return e.messages?.length
															? e.messages.join('\n')
															: e.message;
													}
												}
											);
										}
									});
								}
							},
							{
								label: 'View Job',
								condition: () => row.status !== 'Scheduled',
								onClick() {
									router.push({
										name: 'Site Job',
										params: { name: site.name, id: row.update_job }
									});
								}
							},
							{
								label: 'Update Now',
								condition: () => row.status === 'Scheduled',
								onClick() {
									let siteUpdate = getDocResource({
										doctype: 'Site Update',
										name: row.name,
										whitelistedMethods: {
											updateNow: 'start'
										}
									});

									toast.promise(siteUpdate.updateNow.submit(), {
										loading: 'Updating site...',
										success: () => {
											router.push({
												name: 'Site Jobs',
												params: { name: site.name }
											});

											return 'Site update started';
										},
										error: 'Failed to update site'
									});
								}
							},
							{
								label: 'View App Changes',
								onClick() {
									createListResource({
										doctype: 'Deploy Candidate Difference App',
										fields: [
											'difference.github_diff_url as diff_url',
											'difference.source_hash as source_hash',
											'difference.destination_hash as destination_hash',
											'app.title as app'
										],
										filters: {
											parenttype: 'Deploy Candidate Difference',
											parent: row.difference
										},
										auto: true,
										pageLength: 99,
										onSuccess(data) {
											if (data?.length) {
												renderDialog(
													h(
														GenericDialog,
														{
															options: {
																title: 'App Changes',
																size: '2xl'
															}
														},
														{
															default: () =>
																h(ObjectList, {
																	options: {
																		data: () => data,
																		columns: [
																			{
																				label: 'App',
																				fieldname: 'app'
																			},
																			{
																				label: 'From',
																				fieldname: 'source_hash',
																				type: 'Button',
																				Button({ row }) {
																					return {
																						label:
																							row.source_tag ||
																							row.source_hash.slice(0, 7),
																						variant: 'ghost',
																						class: 'font-mono',
																						link: `${
																							row.diff_url.split('/compare')[0]
																						}/commit/${row.source_hash}`
																					};
																				}
																			},
																			{
																				label: 'To',
																				fieldname: 'destination_hash',
																				type: 'Button',
																				Button({ row }) {
																					return {
																						label:
																							row.destination_tag ||
																							row.destination_hash.slice(0, 7),
																						variant: 'ghost',
																						class: 'font-mono',
																						link: `${
																							row.diff_url.split('/compare')[0]
																						}/commit/${row.destination_hash}`
																					};
																				}
																			},
																			{
																				label: 'App Changes',
																				fieldname: 'diff_url',
																				align: 'right',
																				type: 'Button',
																				Button({ row }) {
																					return {
																						label: 'View',
																						variant: 'ghost',
																						slots: {
																							prefix: icon('external-link')
																						},
																						link: row.diff_url
																					};
																				}
																			}
																		]
																	}
																})
														}
													)
												);
											} else toast.error('No app changes found');
										}
									});
								}
							}
						];
					},
					actions({ documentResource: site }) {
						if (site.doc.group_public) return [];

						return [
							{
								label: 'Configure',
								slots: {
									prefix: icon('settings')
								},
								onClick() {
									let ConfigureAutoUpdateDialog = defineAsyncComponent(() =>
										import('../components/site/ConfigureAutoUpdateDialog.vue')
									);

									renderDialog(
										h(ConfigureAutoUpdateDialog, {
											site: site.doc?.name
										})
									);
								}
							}
						];
					},
					banner({ documentResource: site }) {
						const bannerTitle =
							'Your site is currently on a shared bench group. Upgrade to a private bench group to configure auto updates and <a href="https://frappecloud.com/shared-hosting#benches" class="underline" target="_blank">more</a>.';

						return getUpsellBanner(site, bannerTitle);
					}
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
						return { site: site.doc?.name };
					},
					fields: ['owner', 'job'],
					orderBy: 'creation desc',
					route(row) {
						if (!row.job) return {};

						return {
							name: 'Site Job',
							params: { id: row.job }
						};
					},
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
							label: 'Description',
							fieldname: 'reason',
							class: 'text-gray-600'
						},
						{
							label: '',
							fieldname: 'creation',
							type: 'Timestamp',
							align: 'right'
						}
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
									'Activate Site',
									'Add Domain',
									'Archive',
									'Backup',
									'Create',
									'Clear Cache',
									'Deactivate Site',
									'Disable Database Access',
									'Drop Offsite Backups',
									'Enable Database Access',
									'Install App',
									'Login as Administrator',
									'Migrate',
									'Reinstall',
									'Restore',
									'Suspend Site',
									'Uninstall App',
									'Unsuspend Site',
									'Update',
									'Update Configuration'
								]
							}
						];
					},
					primaryAction({ documentResource: site }) {
						return {
							label: 'Change Notification Email',
							slots: {
								prefix: icon('mail')
							},
							onClick: () => {
								confirmDialog({
									title: 'Change Notification Email',
									fields: [
										{
											type: 'email',
											label: 'Email',
											fieldname: 'email',
											default: site.doc.notify_email
										}
									],
									onSuccess({ hide, values }) {
										return site.setValue.submit(
											{
												notify_email: values.email
											},
											{
												validate: doc => {
													function validateEmail(email) {
														const re = /\S+@\S+\.\S+/;
														return re.test(email);
													}

													let email = doc?.fieldname?.notify_email;
													if (!email) {
														return 'Email is required';
													} else if (!validateEmail(email)) {
														return 'Enter a valid email address';
													}
												},
												onSuccess() {
													hide();
													toast.success('Email updated successfully');
												},
												onError(e) {
													throw new Error(
														e.messages
															? e.messages.join('\n')
															: e.message || 'Error updating email'
													);
												}
											}
										);
									}
								});
							}
						};
					}
				}
			}
		],
		actions(context) {
			let { documentResource: site } = context;
			let $team = getTeam();
			let runningJobs = getRunningJobs({ site: site.doc?.name });

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
							name: 'Site Jobs',
							params: { name: site.name }
						});
					}
				},
				{
					label: 'Update Available',
					variant: site.doc?.setup_wizard_complete ? 'solid' : 'subtle',
					slots: {
						prefix: icon('alert-circle')
					},
					condition() {
						return (
							!site.doc?.has_scheduled_updates &&
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
						renderDialog(h(SiteUpdateDialog, { site: site.doc?.name }));
					}
				},
				{
					label: 'Update Scheduled',
					slots: {
						prefix: icon('calendar')
					},
					condition: () => site.doc?.has_scheduled_updates,
					onClick() {
						router.push({
							name: 'Site Detail Updates',
							params: { name: site.name }
						});
					}
				},
				{
					label: 'Impersonate Site Owner',
					title: 'Impersonate Site Owner', // for label to pop-up on hover
					slots: {
						icon: defineAsyncComponent(() =>
							import('~icons/lucide/venetian-mask')
						)
					},
					condition: () =>
						$team.doc?.is_desk_user && site.doc.team !== $team.name,
					onClick() {
						switchToTeam(site.doc.team);
					}
				},
				{
					label: 'Visit Site',
					slots: {
						prefix: icon('external-link')
					},
					condition: () =>
						site.doc.status !== 'Archived' && site.doc?.setup_wizard_complete,
					onClick() {
						window.open(`https://${site.name}`, '_blank');
					}
				},
				{
					label: 'Setup Site',
					slots: {
						prefix: icon('external-link')
					},
					variant: 'solid',
					condition: () =>
						site.doc.status === 'Active' && !site.doc?.setup_wizard_complete,
					onClick() {
						if (site.doc.additional_system_user_created) {
							site.loginAsTeam
								.submit({ reason: '' })
								.then(url => window.open(url, '_blank'));
						} else {
							site.loginAsAdmin
								.submit({ reason: '' })
								.then(url => window.open(url, '_blank'));
						}
					}
				},
				{
					label: 'Options',
					context,
					options: [
						{
							label: 'View in Desk',
							icon: 'external-link',
							condition: () => $team.doc?.is_desk_user,
							onClick: () => {
								window.open(
									`${window.location.protocol}//${window.location.host}/app/site/${site.name}`,
									'_blank'
								);
							}
						},
						{
							label: 'Login As Administrator',
							icon: 'external-link',
							condition: () => site.doc.status === 'Active',
							onClick: () => {
								confirmDialog({
									title: 'Login as Administrator',
									message: `Are you sure you want to login as administrator on the site <b>${site.doc?.name}</b>?`,
									fields:
										$team.name !== site.doc.team
											? [
													{
														label: 'Reason',
														type: 'textarea',
														fieldname: 'reason'
													}
											  ]
											: [],
									onSuccess: ({ hide, values }) => {
										if (!values.reason && $team.name !== site.doc.team) {
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
	}
};
