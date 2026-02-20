import { LoadingIndicator, Tooltip } from 'frappe-ui';
import { defineAsyncComponent, h } from 'vue';
import { toast } from 'vue-sonner';
import LucideAppWindow from '~icons/lucide/app-window';
import LucideHardDriveDownload from '~icons/lucide/hard-drive-download';
import LucideRocket from '~icons/lucide/rocket';
import AddAppDialog from '../components/group/AddAppDialog.vue';
import ChangeAppBranchDialog from '../components/group/ChangeAppBranchDialog.vue';
import PatchAppDialog from '../components/group/PatchAppDialog.vue';
import { getTeam, switchToTeam } from '../data/team';
import router from '../router';
import { confirmDialog, icon, renderDialog } from '../utils/components';
import { getToastErrorMessage } from '../utils/toast';
import { date, duration } from '../utils/format';
import { getJobsTab } from './common/jobs';
import { getPatchesTab } from './common/patches';
import { tagTab } from './common/tags';

export default {
	doctype: 'Release Group',
	whitelistedMethods: {
		addApp: 'add_app',
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
		getCertificate: 'get_certificate',
		generateCertificate: 'generate_certificate',
		sendTransferRequest: 'send_change_team_request',
		addTag: 'add_resource_tag',
		removeTag: 'remove_resource_tag',
		redeploy: 'redeploy',
		initialDeploy: 'initial_deploy',
	},
	list: {
		route: '/groups',
		title: 'Bench Groups',
		fields: [{ apps: ['app'] }],
		searchField: 'title',
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
		columns: [
			{ label: 'Title', fieldname: 'title', class: 'font-medium' },
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
				class: 'text-gray-600',
				width: 0.25,
			},
		],
		primaryAction() {
			return {
				label: 'New Bench Group',
				variant: 'solid',
				slots: {
					prefix: icon('plus'),
				},
				onClick() {
					router.push({ name: 'New Release Group' });
				},
			};
		},
		banner({ listResource: groups }) {
			if (!groups.data?.length) {
				return {
					title: 'Learn how to create a new private bench group and sites',
					button: {
						label: 'Read docs',
						variant: 'outline',
						link: 'https://docs.frappe.io/cloud/benches/create-new',
					},
				};
			}
		},
	},
	detail: {
		titleField: 'title',
		statusBadge({ documentResource: releaseGroup }) {
			return { label: releaseGroup.doc.status };
		},
		breadcrumbs({ items, documentResource: releaseGroup }) {
			if (!releaseGroup.doc.server_team) return items;

			let breadcrumbs = [];
			let $team = getTeam();

			if (
				releaseGroup.doc.server_team == $team.doc?.name ||
				$team.doc?.is_desk_user
			) {
				breadcrumbs.push(
					{
						label: releaseGroup.doc?.server_title || releaseGroup.doc?.server,
						route: `/servers/${releaseGroup.doc?.server}`,
					},
					items[1],
				);
			} else {
				breadcrumbs.push(...items);
			}
			return breadcrumbs;
		},
		route: '/groups/:name',
		tabs: [
			{
				label: 'Sites',
				icon: icon(LucideAppWindow),
				route: 'sites',
				type: 'Component',
				component: defineAsyncComponent(
					() => import('../pages/ReleaseGroupBenchSites.vue'),
				),
				props: (releaseGroup) => {
					return {
						releaseGroup: releaseGroup.doc.name,
						actionsAccess: releaseGroup.doc.actions_access,
					};
				},
			},
			{
				label: 'Apps',
				icon: icon('grid'),
				route: 'apps',
				type: 'list',
				list: {
					doctype: 'Release Group App',
					filters: (releaseGroup) => {
						return {
							parenttype: 'Release Group',
							parent: releaseGroup.doc.name,
						};
					},
					pageLength: 99999,
					columns: [
						{
							label: 'App',
							fieldname: 'title',
							width: 1,
						},
						{
							label: 'Repository',
							width: 1,
							format(value, row) {
								return `${row.repository_owner}/${row.repository}`;
							},
							link(value, row) {
								return row.repository_url;
							},
						},
						{
							label: 'Branch',
							fieldname: 'branch',
							type: 'Badge',
							width: 0.5,
							link(value, row) {
								return `${row.repository_url}/tree/${value}`;
							},
						},
						{
							label: 'Version',
							type: 'Badge',
							fieldname: 'tag',
							width: 0.5,
							format(value, row) {
								return value || row.hash?.slice(0, 7);
							},
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
										class: 'rounded-full bg-gray-100 p-1',
									},
									() => [
										h(
											'a',
											{
												href: 'https://docs.frappe.io/cloud/faq/app-installation-issue',
												target: '_blank',
											},
											[h(icon('help-circle', 'w-3 h-3'), {})],
										),
									],
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
							width: 0.5,
						},
					],
					rowActions({
						row,
						listResource: apps,
						documentResource: releaseGroup,
					}) {
						let team = getTeam();
						return [
							{
								label: 'View in Desk',
								condition: () => team.doc?.is_desk_user,
								onClick() {
									window.open(
										`${window.location.protocol}//${window.location.host}/app/app/${row.name}`,
										'_blank',
									);
								},
							},
							{
								label: 'Fetch Latest Updates',
								onClick() {
									toast.promise(
										releaseGroup.fetchLatestAppUpdates.submit({
											app: row.name,
										}),
										{
											loading: `Fetching Latest Updates for ${row.title}...`,
											success: () => {
												apps.reload();
												return `Latest Updates Fetched for ${row.title}`;
											},
											error: (e) => getToastErrorMessage(e),
										},
									);
								},
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
											},
										}),
									);
								},
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
													app: row.name,
												}),
												{
													loading: 'Removing App...',
													success: () => {
														hide();
														apps.reload();
														return 'App Removed';
													},
													error: (e) => getToastErrorMessage(e),
												},
											);
										},
									});
								},
							},
							{
								label: 'Visit Repo',
								onClick() {
									window.open(
										`${row.repository_url}/tree/${row.branch}`,
										'_blank',
									);
								},
							},
							{
								label: 'Apply Patch',
								onClick: () => {
									renderDialog(
										h(PatchAppDialog, {
											group: releaseGroup.name,
											app: row.name,
										}),
									);
								},
							},
						];
					},
					primaryAction({
						listResource: apps,
						documentResource: releaseGroup,
					}) {
						return {
							label: 'Add App',
							slots: {
								prefix: icon('plus'),
							},
							onClick() {
								renderDialog(
									h(AddAppDialog, {
										group: releaseGroup.doc,
										onAppAdd() {
											apps.reload();
											releaseGroup.reload();
										},
										onNewApp(app, isUpdate) {
											const loading = isUpdate
												? 'Replacing App...'
												: 'Adding App...';

											toast.promise(
												releaseGroup.addApp.submit({
													app,
													is_update: isUpdate,
												}),
												{
													loading,
													success: () => {
														apps.reload();
														releaseGroup.reload();

														if (isUpdate) {
															return `App ${app.title} updated`;
														}

														return `App ${app.title} added`;
													},
													error: (e) => getToastErrorMessage(e),
												},
											);
										},
									}),
								);
							},
						};
					},
				},
			},
			{
				label: 'Deploys',
				route: 'deploys',
				icon: icon('package'),
				childrenRoutes: ['Deploy Candidate'],
				type: 'list',
				list: {
					doctype: 'Deploy Candidate Build',
					route: (row) => ({
						name: 'Deploy Candidate',
						params: { id: row.name },
					}),
					filters: (releaseGroup) => {
						return {
							group: releaseGroup.name,
						};
					},
					orderBy: 'creation desc',
					// fields: [{ apps: ['app'] }],
					filterControls() {
						return [
							{
								type: 'select',
								label: 'Status',
								fieldname: 'status',
								options: [
									'',
									'Draft',
									'Scheduled',
									'Pending',
									'Preparing',
									'Running',
									'Success',
									'Failure',
								],
							},
						];
					},
					banner({ documentResource: releaseGroup }) {
						if (releaseGroup.doc.are_builds_suspended) {
							return {
								title:
									'<b>Builds Suspended:</b> updates will be scheduled to run when builds resume.',
								type: 'warning',
							};
						} else {
							return null;
						}
					},
					columns: [
						{
							label: 'Deploy',
							fieldname: 'creation',
							format(value) {
								return `Deploy on ${date(value, 'llll')}`;
							},
							width: '20rem',
						},
						{
							label: 'Status',
							fieldname: 'status',
							type: 'Badge',
							width: 0.5,
							suffix(row) {
								if (!row.addressable_notification) {
									return;
								}

								return h(
									Tooltip,
									{
										text: 'Attention required!',
										placement: 'top',
										class: 'rounded-full bg-gray-100 p-1',
									},
									() => h(icon('alert-circle', 'w-3 h-3'), {}),
								);
							},
						},
						{
							label: 'Apps',
							format(value, row) {
								return (row.apps || []).join(', ');
							},
							width: '20rem',
						},
						{
							label: 'Duration',
							fieldname: 'build_duration',
							format: duration,
							class: 'text-gray-600',
							width: 1,
						},
						{
							label: 'Deployed By',
							fieldname: 'owner',
							width: 1,
						},
					],
					primaryAction({ listResource: deploys, documentResource: group }) {
						return {
							label: 'Deploy',
							slots: {
								prefix: icon(LucideRocket),
							},
							onClick() {
								if (group.doc.deploy_information.deploy_in_progress) {
									return toast.error(
										'Deploy is in progress. Please wait for it to complete.',
									);
								} else if (group.doc.deploy_information.update_available) {
									let UpdateReleaseGroupDialog = defineAsyncComponent(
										() =>
											import(
												'../components/group/UpdateReleaseGroupDialog.vue'
											),
									);
									renderDialog(
										h(UpdateReleaseGroupDialog, {
											bench: group.name,
											lastDeploy: true,
											onSuccess(candidate) {
												group.doc.deploy_information.deploy_in_progress = true;
												if (candidate) {
													group.doc.deploy_information.last_deploy.name =
														candidate;
												}
											},
										}),
									);
								} else {
									confirmDialog({
										title: 'Deploy without app updates?',
										message:
											'No app updates detected. Changes in dependencies and environment variables will be applied on deploying.',
										onSuccess: ({ hide }) => {
											toast.promise(group.redeploy.submit(), {
												loading: 'Deploying...',
												success: () => {
													hide();
													deploys.reload();
													return 'Changes Deployed';
												},
												error: (e) => getToastErrorMessage(e),
											});
										},
									});
								}
							},
						};
					},
				},
			},
			getJobsTab('Release Group'),
			{
				label: 'Config',
				icon: icon('settings'),
				route: 'bench-config',
				type: 'list',
				list: {
					doctype: 'Common Site Config',
					filters: (releaseGroup) => {
						return {
							parenttype: 'Release Group',
							parent: releaseGroup.name,
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
							},
						},
						{
							label: 'Config Value',
							fieldname: 'value',
							class: 'font-mono',
						},
						{
							label: 'Type',
							fieldname: 'type',
							type: 'Badge',
							width: '100px',
						},
					],
					primaryAction({
						listResource: configs,
						documentResource: releaseGroup,
					}) {
						return {
							label: 'Add Config',
							slots: {
								prefix: icon('plus'),
							},
							onClick() {
								let ConfigEditorDialog = defineAsyncComponent(
									() => import('../components/ConfigEditorDialog.vue'),
								);
								renderDialog(
									h(ConfigEditorDialog, {
										group: releaseGroup.doc.name,
										onSuccess() {
											configs.reload();
										},
									}),
								);
							},
						};
					},
					secondaryAction({ listResource: configs }) {
						return {
							label: 'Preview',
							slots: {
								prefix: icon('eye'),
							},
							onClick() {
								let ConfigPreviewDialog = defineAsyncComponent(
									() => import('../components/ConfigPreviewDialog.vue'),
								);
								renderDialog(
									h(ConfigPreviewDialog, {
										configs: configs.data,
									}),
								);
							},
						};
					},
					rowActions({
						row,
						listResource: configs,
						documentResource: releaseGroup,
					}) {
						return [
							{
								label: 'Edit',
								onClick() {
									let ConfigEditorDialog = defineAsyncComponent(
										() => import('../components/ConfigEditorDialog.vue'),
									);
									renderDialog(
										h(ConfigEditorDialog, {
											group: releaseGroup.doc.name,
											config: row,
											onSuccess() {
												configs.reload();
											},
										}),
									);
								},
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
														},
													},
												),
												{
													loading: 'Deleting config...',
													success: () => `Config ${row.key} removed`,
													error: (e) => getToastErrorMessage(e),
												},
											);
										},
									});
								},
							},
						];
					},
				},
			},
			{
				label: 'Actions',
				icon: icon('sliders'),
				route: 'actions',
				type: 'Component',
				component: defineAsyncComponent(
					() => import('../components/group/ReleaseGroupActions.vue'),
				),
				props: (releaseGroup) => {
					return { releaseGroup: releaseGroup.name };
				},
			},
			{
				label: 'Regions',
				icon: icon('globe'),
				route: 'regions',
				type: 'list',
				list: {
					doctype: 'Cluster',
					filters: (releaseGroup) => {
						return { group: releaseGroup.name };
					},
					columns: [
						{
							label: 'Region',
							fieldname: 'title',
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
									alt: row.title,
								});
							},
						},
					],
					primaryAction({
						listResource: clusters,
						documentResource: releaseGroup,
					}) {
						return {
							label: 'Add Region',
							slots: {
								prefix: icon('plus'),
							},
							onClick() {
								let AddRegionDialog = defineAsyncComponent(
									() => import('../components/group/AddRegionDialog.vue'),
								);
								renderDialog(
									h(AddRegionDialog, {
										group: releaseGroup.doc.name,
										onSuccess() {
											clusters.reload();
										},
									}),
								);
							},
						};
					},
				},
			},
			getPatchesTab(false),
			{
				label: 'Dependencies',
				icon: icon('box'),
				route: 'bench-dependencies',
				type: 'list',
				list: {
					doctype: 'Release Group Dependency',
					filters: (releaseGroup) => {
						return {
							parenttype: 'Release Group',
							parent: releaseGroup.name,
						};
					},
					columns: [
						{
							label: 'Dependency',
							fieldname: 'dependency',
							format(value, row) {
								return row.title;
							},
						},
						{
							label: 'Version',
							fieldname: 'version',
							suffix(row) {
								if (!row.is_custom) {
									return;
								}

								return h(
									Tooltip,
									{
										text: 'Custom version',
										placement: 'top',
										class: 'rounded-full bg-gray-100 p-1',
									},
									() => h(icon('alert-circle', 'w-3 h-3'), {}),
								);
							},
						},
					],
					rowActions({
						row,
						listResource: dependencies,
						documentResource: releaseGroup,
					}) {
						return [
							{
								label: 'Edit',
								onClick() {
									let DependencyEditorDialog = defineAsyncComponent(
										() =>
											import('../components/group/DependencyEditorDialog.vue'),
									);
									renderDialog(
										h(DependencyEditorDialog, {
											group: releaseGroup.doc,
											dependency: row,
											onSuccess() {
												dependencies.reload();
											},
										}),
									);
								},
							},
						];
					},
				},
			},
			{
				label: 'Env',
				icon: icon('tool'),
				route: 'bench-environment-variable',
				type: 'list',
				list: {
					doctype: 'Release Group Variable',
					filters: (releaseGroup) => {
						return {
							parenttype: 'Release Group',
							parent: releaseGroup.name,
						};
					},
					orderBy: 'creation desc',
					fields: ['name'],
					columns: [
						{
							label: 'Environment Variable Name',
							fieldname: 'key',
						},
						{
							label: 'Environment Variable Value',
							fieldname: 'value',
						},
					],
					primaryAction({
						listResource: environmentVariables,
						documentResource: releaseGroup,
					}) {
						return {
							label: 'Add Environment Variable',
							slots: {
								prefix: icon('plus'),
							},
							onClick() {
								let EnvironmentVariableEditorDialog = defineAsyncComponent(
									() =>
										import('../components/EnvironmentVariableEditorDialog.vue'),
								);
								renderDialog(
									h(EnvironmentVariableEditorDialog, {
										group: releaseGroup.doc.name,
										onSuccess() {
											environmentVariables.reload();
										},
									}),
								);
							},
						};
					},
					rowActions({
						row,
						listResource: environmentVariables,
						documentResource: releaseGroup,
					}) {
						return [
							{
								label: 'Edit',
								onClick() {
									let ConfigEditorDialog = defineAsyncComponent(
										() =>
											import(
												'../components/EnvironmentVariableEditorDialog.vue'
											),
									);
									renderDialog(
										h(ConfigEditorDialog, {
											group: releaseGroup.doc.name,
											environment_variable: row,
											onSuccess() {
												environmentVariables.reload();
											},
										}),
									);
								},
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
														},
													},
												),
												{
													loading: 'Deleting  environment variable...',
													success: () =>
														`Environment variable ${row.key} removed`,
													error: (e) => getToastErrorMessage(e),
												},
											);
										},
									});
								},
							},
						];
					},
				},
			},
			tagTab('Release Group'),
		],
		actions(context) {
			let { documentResource: group } = context;
			let team = getTeam();

			return [
				{
					label: 'Impersonate Group Owner',
					title: 'Impersonate Group Owner', // for label to pop-up on hover
					slots: {
						icon: defineAsyncComponent(
							() => import('~icons/lucide/venetian-mask'),
						),
					},
					condition: () =>
						team.doc?.is_desk_user && group.doc.team !== team.name,
					onClick() {
						switchToTeam(group.doc.team);
					},
				},
				{
					label: group.doc?.deploy_information?.last_deploy
						? 'Update Available'
						: 'Deploy Now',
					slots: {
						prefix: group.doc?.deploy_information?.last_deploy
							? icon(LucideHardDriveDownload)
							: icon(LucideRocket),
					},
					variant: 'solid',
					condition: () =>
						!group.doc.deploy_information.deploy_in_progress &&
						group.doc.deploy_information.update_available &&
						['Awaiting Deploy', 'Active'].includes(group.doc.status),
					onClick() {
						let UpdateReleaseGroupDialog = defineAsyncComponent(
							() => import('../components/group/UpdateReleaseGroupDialog.vue'),
						);
						renderDialog(
							h(UpdateReleaseGroupDialog, {
								bench: group.name,
								lastDeploy: group.doc?.deploy_information?.last_deploy,
								onSuccess(candidate) {
									group.doc.deploy_information.deploy_in_progress = true;
									if (candidate) {
										group.doc.deploy_information.last_deploy = {
											name: candidate,
										};
									}
								},
							}),
						);
					},
				},
				{
					label: 'Deploy in progress',
					slots: {
						prefix: () => h(LoadingIndicator, { class: 'w-4 h-4' }),
					},
					theme: 'green',
					condition: () => group.doc.deploy_information.deploy_in_progress,
					route: {
						name: 'Deploy Candidate',
						params: { id: group.doc?.deploy_information?.last_deploy?.name },
					},
				},
				{
					label: 'Options',
					condition: () => team.doc?.is_desk_user,
					options: [
						{
							label: 'View in Desk',
							icon: icon('external-link'),
							condition: () => team.doc?.is_desk_user,
							onClick() {
								window.open(
									`${window.location.protocol}//${window.location.host}/app/release-group/${group.name}`,
									'_blank',
								);
							},
						},
					],
				},
			];
		},
	},
	routes: [
		{
			name: 'Deploy Candidate',
			path: 'deploys/:id',
			component: () => import('../pages/DeployCandidate.vue'),
		},
		{
			name: 'Release Group Job',
			path: 'jobs/:id',
			component: () => import('../pages/JobPage.vue'),
		},
	],
};
