<template>
	<div>
		<CustomAlerts ctx_type="List Page" />
		<DismissableBanner
			v-if="$releaseGroup.doc.eol_versions.includes($releaseGroup.doc.version)"
			class="col-span-1 lg:col-span-2"
			title="Your sites are on an End of Life version. Upgrade to the latest version to get support, latest features and security updates."
			:id="`${$releaseGroup.name}-eol`"
			type="gray"
		>
			<Button
				class="ml-auto min-w-[7rem]"
				variant="outline"
				link="https://docs.frappe.io/cloud/sites/version-upgrade"
			>
				Upgrade Now
			</Button>
		</DismissableBanner>
		<ObjectList class="mt-3" :options="listOptions" />
		<Dialog
			v-model="showAppVersionDialog"
			:options="{
				title: `Apps in ${$releaseGroup.getAppVersions.params?.args.bench}`,
				size: '6xl',
			}"
		>
			<template #body-content>
				<ObjectList :options="appVersionOptions" />
			</template>
		</Dialog>
	</div>
</template>
<script lang="jsx">
import Badge from '@/components/global/Badge.vue';
import { createResource, getCachedDocumentResource, Tooltip } from 'frappe-ui';
import { defineAsyncComponent, h } from 'vue';
import { toast } from 'vue-sonner';
import ActionButton from '../components/ActionButton.vue';
import SSHCertificateDialog from '../components/group/SSHCertificateDialog.vue';
import ObjectList from '../components/ObjectList.vue';
import {
	getSitesTabColumns,
	sitesTabRoute,
	siteTabFilterControls,
} from '../objects/common';
import { confirmDialog, icon, renderDialog } from '../utils/components';
import { getToastErrorMessage } from '../utils/toast';
import DismissableBanner from '../components/DismissableBanner.vue';
import CustomAlerts from '../components/CustomAlerts.vue';

export default {
	name: 'ReleaseGroupBenchSites',
	props: ['releaseGroup', 'actionsAccess'],
	components: { ObjectList, DismissableBanner, CustomAlerts },
	data() {
		return {
			showAppVersionDialog: false,
			sitesGroupedByBench: [],
		};
	},
	resources: {
		benches() {
			return {
				type: 'list',
				doctype: 'Bench',
				filters: {
					group: this.$releaseGroup.name,
					skip_team_filter_for_system_user_and_support_agent: true,
				},
				fields: ['name', 'status'],
				orderBy: 'creation desc',
				pageLength: 99999,
				auto: true,
				onSuccess() {
					this.$resources.sites.fetch();
				},
			};
		},
		sites() {
			return {
				type: 'list',
				doctype: 'Site',
				filters: {
					group: this.$releaseGroup.name,
					skip_team_filter_for_system_user_and_support_agent: true,
				},
				fields: [
					'name',
					'status',
					'bench',
					'host_name',
					'plan.plan_title as plan_title',
					'plan.price_usd as price_usd',
					'plan.price_inr as price_inr',
					'cluster.image as cluster_image',
					'cluster.title as cluster_title',
				],
				orderBy: 'creation desc, bench desc',
				pageLength: 99999,
				transform(data) {
					return this.groupSitesByBench(data);
				},
				auto: false,
			};
		},
	},
	computed: {
		listOptions() {
			return {
				list: this.$resources.sites,
				groupHeader: ({ group: bench }) => {
					if (!bench?.status) return;

					const options = this.benchOptions(bench);
					const IconHash = icon('hash', 'w-3 h-3');
					const IconStar = icon('star', 'w-3 h-3');
					return (
						<div class="flex items-center">
							<Tooltip text="View bench details">
								<a
									class="text-base font-medium leading-6 text-gray-900 cursor-pointer"
									href={`/dashboard/benches/${bench.name}`}
								>
									{bench.group}
								</a>
							</Tooltip>
							{bench.status != 'Active' ? (
								<Badge class="ml-4" label={bench.status} />
							) : null}
							{bench.has_app_patch_applied && (
								<Tooltip text="Apps in this bench may have been patched">
									<a
										class="p-1 ml-2 text-gray-700 bg-gray-100 rounded"
										href="https://docs.frappe.io/cloud/benches/app-patches"
										target="_blank"
									>
										<IconHash />
									</a>
								</Tooltip>
							)}
							{bench.has_updated_inplace && (
								<Tooltip text="This bench has been updated in place">
									<a
										class="p-1 ml-2 text-gray-700 bg-gray-100 rounded"
										href="https://docs.frappe.io/cloud/in-place-updates"
										target="_blank"
									>
										<IconStar />
									</a>
								</Tooltip>
							)}
							<ActionButton class="ml-auto" options={options} />
						</div>
					);
				},
				emptyStateMessage: this.$releaseGroup.doc.deploy_information.last_deploy
					? 'No sites found'
					: 'Create a deploy first to start creating sites',
				columns: getSitesTabColumns(false),
				filterControls: siteTabFilterControls,
				route: sitesTabRoute,
				primaryAction: () => {
					return {
						label: 'New Site',
						slots: {
							prefix: icon('plus', 'w-4 h-4'),
						},
						disabled: !this.$releaseGroup.doc?.deploy_information?.last_deploy,
						route: {
							name: 'Release Group New Site',
							params: { bench: this.releaseGroup },
						},
					};
				},
			};
		},
		appVersionOptions() {
			return {
				columns: [
					{
						label: 'App',
						fieldname: 'app',
					},
					{
						label: 'Repo',
						fieldname: 'repository',
						format(value, row) {
							return `${row.repository_owner}/${row.repository}`;
						},
						link: (value, row) => {
							return row.repository_url;
						},
					},
					{
						label: 'Branch',
						fieldname: 'branch',
						type: 'Badge',
					},
					{
						label: 'Commit',
						fieldname: 'hash',
						type: 'Badge',
						format(value, row) {
							return value.slice(0, 7);
						},
						link: (value, row) => {
							return `https://github.com/${row.repository_owner}/${row.repository}/commit/${value}`;
						},
					},
					{
						label: 'Tag',
						fieldname: 'tag',
						type: 'Badge',
					},
				],
				data: () => this.$releaseGroup.getAppVersions.data,
			};
		},
		$releaseGroup() {
			return getCachedDocumentResource('Release Group', this.releaseGroup);
		},
	},
	methods: {
		groupSitesByBench(data) {
			if (!this.$resources.benches.data) return [];
			return this.$resources.benches.data.map((bench) => {
				let sites = (data || []).filter((site) => site.bench === bench.name);
				const isLargeDataset = this.$resources.benches.data?.length >= 1000;
				return {
					...bench,
					// To prevent rendering delays for large servers with many benches and sites
					collapsed: isLargeDataset,
					group: bench.name,
					rows: sites,
				};
			});
		},
		benchOptions(bench) {
			if (!bench) return [];

			return [
				{
					label: 'View in Desk',
					condition: () => this.$team?.doc?.is_desk_user,
					onClick: () =>
						window.open(
							`${window.location.protocol}//${window.location.host}/app/bench/${bench.name}`,
							'_blank',
						),
				},
				{
					label: 'Show Apps',
					condition: () => bench.status === 'Active',
					onClick: () => {
						toast.promise(
							this.$releaseGroup.getAppVersions
								.submit({ bench: bench.name })
								.then(() => {
									this.showAppVersionDialog = true;
								}),
							{
								loading: 'Fetching apps...',
								success: 'Fetched apps with versions',
								error: 'Failed to fetch apps',
								duration: 1000,
							},
						);
					},
				},
				{
					label: 'SSH Access',
					condition: () => bench.status === 'Active',
					onClick: () => {
						renderDialog(
							h(SSHCertificateDialog, {
								bench: bench.name,
								releaseGroup: this.$releaseGroup.name,
							}),
						);
					},
				},
				{
					label: 'View Logs',
					condition: () => bench.status === 'Active',
					onClick: () => {
						let BenchLogsDialog = defineAsyncComponent(
							() => import('../components/group/BenchLogsDialog.vue'),
						);

						renderDialog(
							h(BenchLogsDialog, {
								bench: bench.name,
							}),
						);
					},
				},
				{
					label: 'Update All Sites',
					condition: () => bench.status === 'Active' && bench.rows.length > 0,
					onClick: () => {
						confirmDialog({
							title: 'Update All Sites',
							message: `Are you sure you want to update all sites in the bench <b>${bench.name}</b> to the latest bench?`,
							primaryAction: {
								label: 'Update',
								variant: 'solid',
								onClick: ({ hide }) => {
									toast.promise(
										this.runBenchMethod(bench.name, 'update_all_sites'),
										{
											loading: 'Scheduling updates for the sites...',
											success: () => {
												hide();
												return 'Sites have been scheduled for update';
											},
											error: (e) => {
												hide();
												return getToastErrorMessage(
													e,
													'Failed to update sites',
												);
											},
											duration: 1000,
										},
									);
								},
							},
						});
					},
				},
				{
					label: 'Restart Bench',
					condition: () => bench.status === 'Active',
					onClick: () => {
						confirmDialog({
							title: 'Restart Bench',
							message: `Are you sure you want to restart the bench <b>${bench.name}</b>?`,
							primaryAction: {
								label: 'Restart',
								variant: 'solid',
								theme: 'red',
								onClick: ({ hide }) => {
									toast.promise(this.runBenchMethod(bench.name, 'restart'), {
										loading: 'Restarting bench...',
										success: () => {
											hide();
											return 'Bench will restart shortly';
										},
										error: (e) => {
											hide();
											return getToastErrorMessage(e, 'Failed to restart bench');
										},
										duration: 1000,
									});
								},
							},
						});
					},
				},
				{
					label: 'Rebuild Assets',
					condition: () =>
						bench.status === 'Active' &&
						!bench.on_public_server &&
						(Number(this.$releaseGroup.doc.version.split(' ')[1]) > 13 ||
							this.$releaseGroup.doc.version === 'Nightly'),

					onClick: () => {
						confirmDialog({
							title: 'Rebuild Assets',
							message: `Are you sure you want to rebuild assets for the bench <b>${bench.name}</b>?`,
							primaryAction: {
								label: 'Rebuild',
								variant: 'solid',
								theme: 'red',
								onClick: ({ hide }) => {
									toast.promise(this.runBenchMethod(bench.name, 'rebuild'), {
										loading: 'Rebuilding assets...',
										success: () => {
											hide();
											return 'Assets will be rebuilt in the background. This may take a few minutes.';
										},
										error: (e) => {
											hide();
											return getToastErrorMessage(
												e,
												'Failed to rebuild assets',
											);
										},
										duration: 1000,
									});
								},
							},
						});
					},
				},
				{
					label: 'Archive Bench',
					condition: () => true,
					onClick: () => {
						confirmDialog({
							title: 'Archive Bench',
							message: `Are you sure you want to archive the bench <b>${bench.name}</b>?`,
							primaryAction: {
								label: 'Archive',
								variant: 'solid',
								theme: 'red',
								onClick: ({ hide }) => {
									toast.promise(this.runBenchMethod(bench.name, 'archive'), {
										loading: 'Scheduling bench for archival...',
										success: () => {
											hide();
											return 'Bench is scheduled for archival';
										},
										error: (e) =>
											getToastErrorMessage(e, 'Failed to archive bench'),
									});
								},
							},
						});
					},
				},
				{
					label: 'View Processes',
					condition: () => bench.status === 'Active',
					onClick: () => {
						let SupervisorProcessesDialog = defineAsyncComponent(
							() => import('../components/group/SupervisorProcessesDialog.vue'),
						);

						renderDialog(
							h(SupervisorProcessesDialog, {
								bench: bench.name,
							}),
						);
					},
				},
			].filter((option) => {
				const hasAccess = this.actionsAccess[option.label] ?? true;
				if (!hasAccess) return false;
				if (!option.condition?.()) return false;
				return true;
			});
		},
		runBenchMethod(name, methodName) {
			const method = createResource({
				url: 'press.api.client.run_doc_method',
			});
			return method.submit({
				dt: 'Bench',
				dn: name,
				method: methodName,
			});
		},
	},
};
</script>
