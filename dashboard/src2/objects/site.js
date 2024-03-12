import { frappeRequest, LoadingIndicator, Button } from 'frappe-ui';
import { defineAsyncComponent, h } from 'vue';
import { toast } from 'vue-sonner';
import HelpIcon from '~icons/lucide/help-circle';
import AddDomainDialog from '../components/AddDomainDialog.vue';
import GenericDialog from '../components/GenericDialog.vue';
import ObjectList from '../components/ObjectList.vue';
import { getTeam } from '../data/team';
import router from '../router';
import { confirmDialog, icon, renderDialog } from '../utils/components';
import {
	bytes,
	duration,
	date,
	userCurrency,
	commaAnd,
	plural
} from '../utils/format';
import { dayjsLocal } from '../utils/dayjs';
import { getRunningJobs } from '../utils/agentJob';
import SiteActions from '../components/SiteActions.vue';
import { tagTab } from './common/tags';
import { getPlans } from '../data/plans';

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
						let today = dayjsLocal();
						let diffHours = trialEndDate.diff(today, 'hours');
						let endsIn = '';
						if (diffHours < 24) {
							endsIn = `today`;
						} else {
							let days = Math.round(diffHours / 24);
							endsIn = `in ${days} ${plural(days, 'day', 'days')}`;
						}
						if (
							trialEndDate.isAfter(today) ||
							trialEndDate.isSame(today, 'day')
						) {
							return `Trial ends ${endsIn}`;
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
					router.push({ name: 'New Site' });
				}
			};
		}
	},
	create: {
		title: 'New Site',
		route: '/sites/new',
		secondaryCreate: {
			route: '/benches/:name/sites/new',
			optionalFields: [],
			routeName: 'Bench New Site',
			propName: 'bench'
		},
		optionsResource({ routerProp: bench }) {
			return {
				url: 'press.api.site.options_for_new',
				makeParams() {
					return { for_bench: bench };
				},
				auto: true,
				initialData: {
					versions: [],
					domain: '',
					marketplace_details: {},
					app_source_details: {}
				}
			};
		},
		createResource() {
			return {
				url: 'press.api.client.insert',
				validate({ doc: { subdomain } }) {
					if (!subdomain) {
						return 'Please enter a subdomain';
					}
				},
				onSuccess: site => {
					router.push({
						name: 'Site Detail Jobs',
						params: { name: site.name }
					});
				}
			};
		},
		primaryAction({ createResource: createSite, vals, optionsData }) {
			return {
				label: 'Create Site',
				variant: 'solid',
				onClick() {
					let $team = getTeam();
					if (!vals.apps) vals.apps = [];

					let appPlans = {};
					vals.apps.forEach(app => {
						appPlans[app.app] = app.plan;
					});

					createSite.submit({
						doc: {
							doctype: 'Site',
							team: $team.doc.name,
							subdomain: vals.subdomain,
							apps: [{ app: 'frappe' }, ...vals.apps],
							app_plans: appPlans,
							cluster: vals.cluster,
							bench: optionsData.versions.find(v => v.name === vals.siteVersion)
								.group.bench,
							subscription_plan: vals.plan.name,
							share_details_consent: vals.shareDetailsConsent
						}
					});
				}
			};
		},
		options: [
			{
				label: 'Select Frappe Framework Version',
				name: 'siteVersion',
				type: 'card',
				fieldname: 'versions'
			},
			{
				label: '',
				fieldname: 'apps',
				name: 'apps',
				type: 'Component',
				component({ optionsData, vals }) {
					let NewSiteAppSelector = defineAsyncComponent(() =>
						import('../components/site/NewSiteAppSelector.vue')
					);

					let selectedVersion = optionsData?.versions.find(
						v => v.name === vals.siteVersion
					);
					let selectedVersionApps;

					if (selectedVersion?.group?.bench_app_sources)
						// sorted by total installs and then by name
						selectedVersionApps = selectedVersion.group.bench_app_sources
							.map(app_source => {
								let app_source_details =
									optionsData.app_source_details[app_source];
								let marketplace_details = app_source_details
									? optionsData.marketplace_details[app_source_details.app]
									: {};
								return {
									app_title: app_source,
									...app_source_details,
									...marketplace_details
								};
							})
							.sort((a, b) => {
								if (a.total_installs > b.total_installs) {
									return -1;
								} else if (a.total_installs < b.total_installs) {
									return 1;
								} else {
									return a.app_title.localeCompare(b.app_title);
								}
							});

					return h(NewSiteAppSelector, {
						availableApps: selectedVersionApps,
						siteOnPublicBench: !vals.bench
					});
				},
				dependsOn: ['siteVersion']
			},
			{
				label: 'Select Region',
				name: 'cluster',
				type: 'card',
				dependsOn: ['siteVersion'],
				filter(_, vals, optionsData) {
					return optionsData.versions.find(v => v.name === vals.siteVersion)
						?.group.clusters;
				}
			},
			{
				label: 'Select Plan',
				name: 'plan',
				type: 'plan',
				dependsOn: ['siteVersion', 'cluster'],
				labelSlot() {
					return h(
						Button,
						{
							link: 'https://frappecloud.com/pricing',
							variant: 'ghost'
						},
						{
							prefix: () => h(HelpIcon, { class: 'h-4 w-4 text-gray-700' }),
							default: () => 'Help'
						}
					);
				},
				filter() {
					return getPlans().map(plan => ({
						...plan,
						features: [
							{
								label: 'compute hours / day',
								value: plan.cpu_time_per_day
							},
							{
								label: 'database',
								value: bytes(plan.max_database_usage, 0, 2)
							},
							{
								label: 'disk',
								value: bytes(plan.max_storage_usage, 0, 2)
							},
							{
								label: '',
								value: plan.support_included ? 'Support Included' : ''
							},
							{
								label: '',
								value: plan.database_access ? 'Database Access' : ''
							},
							{
								label: '',
								value: plan.offsite_backups ? 'Offsite Backups' : ''
							},
							{
								label: '',
								value: plan.monitor_access ? 'Advanced Monitoring' : ''
							}
						]
					}));
				}
			},
			{
				label: 'Enter Subdomain',
				name: 'subdomain',
				type: 'Component',
				component({ optionsData }) {
					let SubdomainInput = defineAsyncComponent(() =>
						import('../components/site/SubdomainInput.vue')
					);

					return h(SubdomainInput, {
						domain: optionsData.domain
					});
				},
				dependsOn: ['siteVersion', 'cluster', 'plan']
			}
		],
		consents: [
			{
				label: 'I am okay if my details are shared with local partners',
				name: 'shareDetailsConsent'
			}
		],
		summary: [
			{
				label: 'Frappe Framework Version',
				fieldname: 'siteVersion'
			},
			{
				label: 'Apps',
				optional: true,
				format(values, optionsData) {
					let apps = (values.apps || []).map(app => app.app);
					if (!apps.length) return 'No apps selected';

					let appTitles = Object.values(optionsData.app_source_details)
						.filter(app => apps.includes(app.app))
						.map(app => app.app_title);

					return commaAnd(appTitles);
				}
			},
			{
				label: 'Region',
				fieldname: 'cluster'
			},
			{
				label: 'Site URL',
				fieldname: 'subdomain',
				format(value, optionsData) {
					return `${value}.${optionsData?.domain}`;
				}
			},
			{
				label: 'Site Plan',
				fieldname: 'plan',
				format(value) {
					let $team = getTeam();

					return `${userCurrency(
						$team.doc.currency == 'INR' ? value.price_inr : value.price_usd
					)} / mo`;
				}
			},
			{
				label: 'Product Warranty',
				fieldname: 'plan',
				format(value) {
					return value.support_included ? 'Included' : 'Not Included';
				}
			},
			{
				label: 'App Plans',
				optional: true,
				format(values, optionsData) {
					if (!values.apps || !values.apps.length) return '';

					let $team = getTeam();
					let description = '';

					for (let app of values.apps) {
						let appTitle = Object.values(optionsData.app_source_details).find(
							a => a.app == app.app
						).app_title;

						if (app.plan) {
							let isAppFree =
								app.plan.price_inr === 0 && app.plan.price_usd === 0;
							description += `<span class="text-gray-900">${appTitle} Plan: </span><span class="text-gray-600">${
								isAppFree
									? 'Free'
									: userCurrency(
											$team.doc.currency == 'INR'
												? app.plan.price_inr
												: app.plan.price_usd
									  )
							}${isAppFree ? '' : ' / mo'}</span><br>`;
						} else {
							description += `<span class="text-gray-900">${appTitle} Plan: </span><span class="text-gray-600">Free</span><br>`;
						}
					}
					return description;
				}
			},
			{
				label: 'Total',
				format(values) {
					let $team = getTeam();
					let appPlans = (values.apps || []).map(app => app.plan);
					let sitePlan = values.plan;

					let total = 0;
					if (sitePlan) {
						total +=
							$team.doc.currency == 'INR'
								? sitePlan.price_inr
								: sitePlan.price_usd;
					}
					for (let app of appPlans) {
						if (app) {
							total +=
								$team.doc.currency == 'INR' ? app.price_inr : app.price_usd;
						}
					}
					return `<span class="text-gray-900">${userCurrency(
						total
					)} / mo</span><br><span class="text-gray-600"> ${userCurrency(
						total / 30
					)} / day</span>`;
				}
			}
		]
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
					return { siteName: site.doc.name };
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

																			if (row.plans) {
																				let SiteAppPlanSelectDialog =
																					defineAsyncComponent(() =>
																						import(
																							'../components/site/SiteAppPlanSelectDialog.vue'
																						)
																					);

																				renderDialog(
																					h(SiteAppPlanSelectDialog, {
																						app: row,
																						currentPlan: null,
																						onPlanSelected(plan) {
																							toast.promise(
																								site.installApp.submit({
																									app: row.app,
																									plan: plan.name
																								}),
																								{
																									loading: 'Installing app...',
																									success: () => {
																										apps.reload();
																										return 'App will be installed shortly';
																									},
																									error: e => {
																										return e.messages.length
																											? e.messages.join('\n')
																											: e.message;
																									}
																								}
																							);
																						}
																					})
																				);
																			} else {
																				toast.promise(
																					site.installApp.submit({
																						app: row.app
																					}),
																					{
																						loading: 'Installing app...',
																						success: () => {
																							apps.reload();
																							return 'App will be installed shortly';
																						},
																						error: e => {
																							return e.messages.length
																								? e.messages.join('\n')
																								: e.message;
																						}
																					}
																				);
																			}
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
										import('../components/site/SiteAppPlanSelectDialog.vue')
									);
									renderDialog(
										h(SiteAppPlanChangeDialog, {
											app: row,
											currentPlan: row.plans.find(
												plan => plan.name === row.plan_info.name
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
					label: 'Impersonate Site Owner',
					slots: {
						prefix: defineAsyncComponent(() =>
							import('~icons/lucide/venetian-mask')
						)
					},
					condition: () =>
						$team.doc.is_desk_user && site.doc.team != $team.name,
					onClick() {
						window.location.href = `/dashboard-beta/impersonate/${site.doc.team}`;
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
