import { LoadingIndicator, Tooltip } from 'frappe-ui';
import { defineAsyncComponent, h } from 'vue';
import { toast } from 'vue-sonner';
import { duration, date } from '../utils/format';
import { icon, renderDialog, confirmDialog } from '../utils/components';
import { getTeam, switchToTeam } from '../data/team';
import router from '../router';
import ChangeAppBranchDialog from '../components/bench/ChangeAppBranchDialog.vue';
import AddAppDialog from '../components/bench/AddAppDialog.vue';
import LucideAppWindow from '~icons/lucide/app-window';
import { tagTab } from './common/tags';

export default {
	doctype: 'Release Group',
	whitelistedMethods: {
		removeApp: 'remove_app',
		changeAppBranch: 'change_app_branch',
		fetchLatestAppUpdates: 'fetch_latest_app_update',
		deleteConfig: 'delete_config',
		updateConfig: 'update_config',
		updateEnvironmentVariable: 'update_environment_variable',
		deleteEnvironmentVariable: 'delete_environment_variable',
		updateDependency: 'update_dependency',
		addRegion: 'add_region',
		deployedVersions: 'deployed_versions',
		getAppVersions: 'get_app_versions',
		archive: 'archive',
		getCertificate: 'get_certificate',
		generateCertificate: 'generate_certificate',
		addTag: 'add_resource_tag',
		removeTag: 'remove_resource_tag'
	},
	list: {
		route: '/benches',
		title: 'Benches',
		fields: [{ apps: ['app'] }],
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
		primaryAction({ listResource: benches }) {
			return {
				label: 'New Bench',
				variant: 'solid',
				slots: {
					prefix: icon('plus')
				},
				onClick() {
					router.push({ name: 'New Release Group' });
				}
			};
		}
	},
	create: {
		route: '/benches/new',
		title: 'New Bench',
		secondaryCreate: {
			route: '/servers/:name/benches/new',
			optionalFields: ['benchRegion'],
			routeName: 'Server New Bench',
			propName: 'server'
		},
		optionsResource() {
			return {
				url: 'press.api.bench.options',
				initialData: {
					versions: [],
					clusters: []
				},
				auto: true
			};
		},
		createResource() {
			return {
				url: 'press.api.bench.new',
				validate({ bench }) {
					if (!bench.title) {
						return 'Bench Title cannot be blank';
					}
					if (!bench.version) {
						return 'Select a version to create bench';
					}
				},
				onSuccess(groupName) {
					this.$router.push({
						name: 'Release Group Detail Apps',
						params: { name: groupName }
					});
				}
			};
		},
		primaryAction({ createResource: createBench, vals, optionsData: options }) {
			return {
				label: 'Create Bench',
				variant: 'solid',
				onClick() {
					createBench.submit({
						bench: {
							title: vals.benchTitle,
							version: vals.benchVersion,
							cluster: vals.benchRegion || null,
							saas_app: null,
							apps: [
								// some wizardry to only pick frappe for the chosen version
								options.versions
									.find(v => v.name === vals.benchVersion)
									.apps.find(app => app.name === 'frappe')
							].map(app => {
								return {
									name: app.name,
									source: app.source.name
								};
							}),
							server: vals.server || null
						}
					});
				}
			};
		},
		options: [
			{
				label: 'Title',
				name: 'benchTitle',
				type: 'text'
			},
			{
				label: 'Select Frappe Framework Version',
				name: 'benchVersion',
				type: 'card',
				fieldname: 'versions',
				dependsOn: ['benchTitle']
			},
			{
				label: 'Select Region',
				name: 'benchRegion',
				type: 'card',
				fieldname: 'clusters',
				dependsOn: ['benchVersion']
			}
		],
		summary: [
			{
				label: 'Bench Title',
				fieldname: 'benchTitle'
			},
			{
				label: 'Region',
				fieldname: 'benchRegion',
				hideWhen: 'server'
			},
			{
				label: 'Server',
				fieldname: 'server',
				hideWhen: 'benchRegion'
			},
			{
				label: 'Frappe Version',
				fieldname: 'benchVersion'
			}
		]
	},
	detail: {
		titleField: 'title',
		statusBadge({ documentResource: releaseGroup }) {
			return { label: releaseGroup.doc.status };
		},
		route: '/benches/:name',
		tabs: [
			{
				label: 'Sites',
				icon: icon(LucideAppWindow),
				route: 'sites',
				type: 'Component',
				component: defineAsyncComponent(() =>
					import('../pages/ReleaseGroupBenchSites.vue')
				),
				props: releaseGroup => {
					return { releaseGroup: releaseGroup.doc.name };
				}
			},
			{
				label: 'Apps',
				icon: icon('grid'),
				route: 'apps',
				type: 'list',
				list: {
					doctype: 'Release Group App',
					filters: releaseGroup => {
						return {
							parenttype: 'Release Group',
							parent: releaseGroup.doc.name
						};
					},
					columns: [
						{
							label: 'App',
							fieldname: 'title',
							width: 1
						},
						{
							label: 'Repo',
							width: 1,
							format(value, row) {
								return `${row.repository_owner}/${row.repository}`;
							},
							link(value, row) {
								return row.repository_url;
							}
						},
						{
							label: 'Branch',
							fieldname: 'branch',
							type: 'Badge',
							width: 1,
							link(value, row) {
								return `${row.repository_url}/tree/${value}`;
							}
						},
						{
							label: 'Status',
							type: 'Badge',
							suffix(row) {
								if (!row.last_github_poll_failed) return;

								return h(
									Tooltip,
									{
										text: "What's this?",
										placement: 'top',
										class: 'rounded-full bg-gray-100 p-1'
									},
									() => [
										h(
											'a',
											{
												href: 'https://frappecloud.com/docs/faq/custom_apps#why-does-it-show-attention-required-next-to-my-custom-app',
												target: '_blank'
											},
											[h(icon('help-circle', 'w-3 h-3'), {})]
										)
									]
								);
							},
							format(value, row) {
								let { update_available, deployed, last_github_poll_failed } =
									row;

								return last_github_poll_failed
									? 'Action Required'
									: !deployed
									? 'Not Deployed'
									: update_available
									? 'Update Available'
									: 'Latest Version';
							},
							width: 1
						}
					],
					rowActions({
						row,
						listResource: apps,
						documentResource: releaseGroup
					}) {
						let team = getTeam();
						return [
							{
								label: 'View in Desk',
								condition: () => team.doc.is_desk_user,
								onClick() {
									window.open(
										`${window.location.protocol}//${window.location.host}/app/release-group/${releaseGroup.name}`,
										'_blank'
									);
								}
							},
							{
								label: 'Fetch Latest Updates',
								onClick() {
									toast.promise(
										releaseGroup.fetchLatestAppUpdates.submit({
											app: row.name
										}),
										{
											loading: `Fetching Latest Updates for ${row.title}...`,
											success: () => {
												apps.reload();
												return `Latest Updates Fetched for ${row.title}`;
											},
											error: e => {
												return e.messages.length
													? e.messages.join('\n')
													: e.message;
											}
										}
									);
								}
							},
							{
								label: 'Change Branch',
								onClick() {
									renderDialog(
										h(ChangeAppBranchDialog, {
											bench: releaseGroup.name,
											app: row,
											onBranchChange() {
												apps.reload();
											}
										})
									);
								}
							},
							{
								label: 'Remove App',
								condition: () => row.name !== 'frappe',
								onClick() {
									if (releaseGroup.removeApp.loading) return;
									confirmDialog({
										title: 'Remove App',
										message: `Are you sure you want to remove the app <b>${row.title}</b>?`,
										onSuccess: ({ hide }) => {
											toast.promise(
												releaseGroup.removeApp.submit({
													app: row.name
												}),
												{
													loading: 'Removing App...',
													success: () => {
														hide();
														apps.reload();
														return 'App Removed';
													},
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
							},
							{
								label: 'Visit Repo',
								onClick() {
									window.open(
										`${row.repository_url}/tree/${row.branch}`,
										'_blank'
									);
								}
							}
						];
					},
					primaryAction({
						listResource: apps,
						documentResource: releaseGroup
					}) {
						return {
							label: 'Add App',
							slots: {
								prefix: icon('plus')
							},
							onClick() {
								renderDialog(
									h(AddAppDialog, {
										benchName: releaseGroup.name,
										onAppAdd() {
											apps.reload();
											releaseGroup.reload();
										}
									})
								);
							}
						};
					}
				}
			},
			{
				label: 'Deploys',
				route: 'deploys',
				icon: icon('package'),
				childrenRoutes: ['Bench Deploy'],
				type: 'list',
				list: {
					doctype: 'Deploy Candidate',
					route: row => ({ name: 'Bench Deploy', params: { id: row.name } }),
					filters: releaseGroup => {
						return {
							group: releaseGroup.name
						};
					},
					orderBy: 'creation desc',
					fields: [{ apps: ['app'] }],
					columns: [
						{
							label: 'Deploy',
							fieldname: 'creation',
							format(value) {
								return `Deploy on ${date(value, 'llll')}`;
							},
							width: '20rem'
						},
						{
							label: 'Status',
							fieldname: 'status',
							type: 'Badge',
							width: 0.5
						},
						{
							label: 'Apps',
							format(value, row) {
								return (row.apps || []).map(d => d.app).join(', ');
							},
							width: '20rem'
						},
						{
							label: 'Duration',
							fieldname: 'build_duration',
							format: duration,
							class: 'text-gray-600',
							width: 1
						},
						{
							label: 'Deployed By',
							fieldname: 'owner',
							width: 1
						}
					]
				}
			},
			{
				label: 'Jobs',
				icon: icon('truck'),
				// highlight: route =>
				// 	['Site Detail Jobs', 'Site Job'].includes(route.name),
				route: 'jobs',
				type: 'list',
				list: {
					doctype: 'Agent Job',
					filters: releaseGroup => {
						return { group: releaseGroup.doc.name };
					},
					route(row) {
						return {
							name: 'Bench Job',
							params: { id: row.name }
						};
					},
					fields: ['end'],
					orderBy: 'creation desc',
					columns: [
						{
							label: 'Job Type',
							fieldname: 'job_type',
							width: '13rem'
						},
						{
							label: 'Status',
							fieldname: 'status',
							type: 'Badge',
							width: '7rem'
						},
						{
							label: 'Site',
							fieldname: 'site',
							class: 'text-gray-600'
						},
						{
							label: 'Job ID',
							fieldname: 'job_id',
							class: 'text-gray-600',
							width: '7rem'
						},
						{
							label: 'Duration',
							fieldname: 'duration',
							class: 'text-gray-600',
							width: '4rem',
							format(value, row) {
								if (row.job_id === 0 || !row.end) return;
								return duration(value);
							}
						},
						{
							label: 'Created By',
							fieldname: 'owner',
							width: '10rem'
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
				label: 'Config',
				icon: icon('settings'),
				route: 'bench-config',
				type: 'list',
				list: {
					doctype: 'Common Site Config',
					filters: releaseGroup => {
						return {
							parenttype: 'Release Group',
							parent: releaseGroup.name
						};
					},
					orderBy: 'creation desc',
					fields: ['name'],
					pageLength: 999,
					columns: [
						{
							label: 'Config Name',
							fieldname: 'key',
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
					primaryAction({
						listResource: configs,
						documentResource: releaseGroup
					}) {
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
										group: releaseGroup.doc.name,
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
					rowActions({
						row,
						listResource: configs,
						documentResource: releaseGroup
					}) {
						return [
							{
								label: 'Edit',
								onClick() {
									let ConfigEditorDialog = defineAsyncComponent(() =>
										import('../components/ConfigEditorDialog.vue')
									);
									renderDialog(
										h(ConfigEditorDialog, {
											group: releaseGroup.doc.name,
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
											if (releaseGroup.deleteConfig.loading) return;
											toast.promise(
												releaseGroup.deleteConfig.submit(
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
				label: 'Environment Variable',
				icon: icon('tool'),
				route: 'bench-environment-variable',
				type: 'list',
				list: {
					doctype: 'Release Group Variable',
					filters: releaseGroup => {
						return {
							parenttype: 'Release Group',
							parent: releaseGroup.name
						};
					},
					orderBy: 'creation desc',
					fields: ['name'],
					columns: [
						{
							label: 'Environment Variable Name',
							fieldname: 'key'
						},
						{
							label: 'Environment Variable Value',
							fieldname: 'value'
						}
					],
					primaryAction({
						listResource: environmentVariables,
						documentResource: releaseGroup
					}) {
						return {
							label: 'Add Environment Variable',
							slots: {
								prefix: icon('plus')
							},
							onClick() {
								let EnvironmentVariableEditorDialog = defineAsyncComponent(() =>
									import('../components/EnvironmentVariableEditorDialog.vue')
								);
								renderDialog(
									h(EnvironmentVariableEditorDialog, {
										group: releaseGroup.doc.name,
										onSuccess() {
											environmentVariables.reload();
										}
									})
								);
							}
						};
					},
					rowActions({
						row,
						listResource: environmentVariables,
						documentResource: releaseGroup
					}) {
						return [
							{
								label: 'Edit',
								onClick() {
									let ConfigEditorDialog = defineAsyncComponent(() =>
										import('../components/EnvironmentVariableEditorDialog.vue')
									);
									renderDialog(
										h(ConfigEditorDialog, {
											group: releaseGroup.doc.name,
											environment_variable: row,
											onSuccess() {
												environmentVariables.reload();
											}
										})
									);
								}
							},
							{
								label: 'Delete',
								onClick() {
									confirmDialog({
										title: 'Delete Environment Variable',
										message: `Are you sure you want to delete the environment variable <b>${row.key}</b>?`,
										onSuccess({ hide }) {
											if (releaseGroup.deleteEnvironmentVariable.loading)
												return;
											toast.promise(
												releaseGroup.deleteEnvironmentVariable.submit(
													{ key: row.key },
													{
														onSuccess: () => {
															environmentVariables.reload();
															hide();
														}
													}
												),
												{
													loading: 'Deleting  environment variable...',
													success: () =>
														`Environment variable ${row.key} removed`,
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
				label: 'Dependencies',
				icon: icon('box'),
				route: 'bench-dependencies',
				type: 'list',
				list: {
					doctype: 'Release Group Dependency',
					filters: releaseGroup => {
						return {
							parenttype: 'Release Group',
							parent: releaseGroup.name
						};
					},
					columns: [
						{
							label: 'Dependency',
							fieldname: 'dependency',
							format(value, row) {
								return row.title;
							}
						},
						{
							label: 'Version',
							fieldname: 'version'
						}
					],
					rowActions({
						row,
						listResource: dependencies,
						documentResource: releaseGroup
					}) {
						return [
							{
								label: 'Edit',
								onClick() {
									let DependencyEditorDialog = defineAsyncComponent(() =>
										import('../components/bench/DependencyEditorDialog.vue')
									);
									renderDialog(
										h(DependencyEditorDialog, {
											group: releaseGroup.doc,
											dependency: row,
											onSuccess() {
												dependencies.reload();
											}
										})
									);
								}
							}
						];
					}
				}
			},
			{
				label: 'Regions',
				icon: icon('globe'),
				route: 'regions',
				type: 'list',
				list: {
					doctype: 'Cluster',
					filters: releaseGroup => {
						return { group: releaseGroup.name };
					},
					columns: [
						{
							label: 'Region',
							fieldname: 'title'
						},
						{
							label: 'Country',
							fieldname: 'image',
							format(value, row) {
								return '';
							},
							prefix(row) {
								return h('img', {
									src: row.image,
									class: 'w-4 h-4',
									alt: row.title
								});
							}
						}
					],
					primaryAction({
						listResource: clusters,
						documentResource: releaseGroup
					}) {
						return {
							label: 'Add Region',
							slots: {
								prefix: icon('plus')
							},
							onClick() {
								let AddRegionDialog = defineAsyncComponent(() =>
									import('../components/bench/AddRegionDialog.vue')
								);
								renderDialog(
									h(AddRegionDialog, {
										group: releaseGroup.doc.name,
										onSuccess() {
											clusters.reload();
										}
									})
								);
							}
						};
					}
				}
			},
			tagTab()
		],
		actions(context) {
			let { documentResource: bench } = context;
			return [
				{
					label: 'Update Available',
					slots: {
						prefix: icon('alert-circle')
					},
					variant: 'solid',
					condition: () =>
						!bench.doc.deploy_information.deploy_in_progress &&
						bench.doc.deploy_information.update_available &&
						['Awaiting Deploy', 'Active'].includes(bench.doc.status),
					onClick() {
						let UpdateBenchDialog = defineAsyncComponent(() =>
							import('../components/bench/UpdateBenchDialog.vue')
						);
						renderDialog(
							h(UpdateBenchDialog, {
								bench: bench.name,
								onSuccess(candidate) {
									bench.doc.deploy_information.deploy_in_progress = true;
									bench.doc.deploy_information.last_deploy.name = candidate;
								}
							})
						);
					}
				},
				{
					label: 'Deploy in progress',
					slots: {
						prefix: () => h(LoadingIndicator, { class: 'w-4 h-4' })
					},
					theme: 'green',
					condition: () => bench.doc.deploy_information.deploy_in_progress,
					route: {
						name: 'Bench Deploy',
						params: { id: bench.doc?.deploy_information?.last_deploy?.name }
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
					options: [
						{
							label: 'Impersonate Team',
							condition: () => window.is_system_user,
							onClick() {
								switchToTeam(bench.doc.team);
							}
						},
						{
							label: 'Drop Bench',
							onClick() {
								confirmDialog({
									title: 'Drop Bench',
									message: `Are you sure you want to drop this bench <b>${bench.doc.title}</b>? All the sites on this bench should be dropped manually before dropping the bench. This action cannot be undone.`,
									fields: [
										{
											label:
												'Please type the exact bench name below to confirm',
											fieldname: 'confirmBenchName',
											autocomplete: 'off'
										}
									],
									primaryAction: {
										label: 'Drop Bench',
										theme: 'red'
									},
									onSuccess({ hide, values }) {
										if (bench.archive.loading) return;
										if (values.confirmBenchName !== bench.doc.title) {
											throw new Error('Bench name does not match');
										}
										return bench.archive.submit(null, {
											onSuccess: () => {
												hide();
												router.push({ name: 'Release Group List' });
											}
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
			name: 'Bench Deploy',
			path: 'deploy/:id',
			component: () => import('../pages/BenchDeploy.vue')
		},
		{
			name: 'Bench Job',
			path: 'job/:id',
			component: () => import('../pages/JobPage.vue')
		}
	]
};
