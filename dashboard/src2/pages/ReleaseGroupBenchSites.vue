<template>
	<div>
		<div class="flex items-center justify-between">
			<div></div>
			<Button
				:route="{ name: 'NewBenchSite', params: { bench: this.releaseGroup } }"
			>
				<template #prefix>
					<i-lucide-plus class="h-4 w-4 text-gray-600" />
				</template>
				New Site
			</Button>
		</div>
		<GenericList class="mt-3" :options="options" />
		<Dialog
			v-model="showAppVersionDialog"
			:options="{ title: 'Apps', size: '3xl' }"
		>
			<template #body-content>
				<div class="mb-4 text-base font-medium">
					{{ $releaseGroup.getAppVersions.params.args.bench }}
				</div>
				<GenericList :options="appVersionOptions" />
			</template>
		</Dialog>
	</div>
</template>
<script>
import { h } from 'vue';
import { getCachedDocumentResource } from 'frappe-ui';
import GenericList from '../components/GenericList.vue';
import { confirmDialog, icon, renderDialog } from '../utils/components';
import { toast } from 'vue-sonner';
import SSHCertificateDialog from '../components/bench/SSHCertificateDialog.vue';

export default {
	name: 'ReleaseGroupBenchSites',
	props: ['releaseGroup'],
	data() {
		return {
			showAppVersionDialog: false
		};
	},
	mounted() {
		this.$releaseGroup.deployedVersions.fetch();
	},
	computed: {
		options() {
			let data = [];
			for (let version of this.deployedVersions.data || []) {
				data.push({
					name: version.name,
					status: version.status,
					proxyServer: version.proxy_server,
					hasSSHAcess: version.has_ssh_access,
					isBench: true
				});
				for (let site of version.sites) {
					data.push(site);
				}
				if (version.sites.length === 0) {
					data.push({
						name: 'No sites'
					});
				}
			}

			return {
				data,
				columns: [
					{
						label: 'Site',
						fieldname: 'name',
						width: 2,
						class({ row }) {
							return row.isBench
								? 'text-gray-900 font-medium'
								: row.name == 'No sites'
								? 'text-gray-600 pl-2'
								: 'text-gray-900 pl-2';
						}
					},
					{
						label: 'Status',
						fieldname: 'status',
						type: 'Badge'
					},
					{
						label: 'Region',
						fieldname: 'server_region_info',
						format(value) {
							return value?.title || '';
						},
						prefix(row) {
							if (row.server_region_info)
								return h('img', {
									src: row.server_region_info.image,
									class: 'w-4 h-4',
									alt: row.server_region_info.title
								});
						}
					},
					{
						label: 'Plan',
						fieldname: 'plan',
						format: value => {
							if (!value) return '';
							if (value.price_usd > 0) {
								let india = this.$team.doc.country == 'India';
								let currencySymbol =
									this.$team.doc.currency == 'INR' ? '₹' : '$';
								return `${currencySymbol}${
									india ? value.price_inr : value.price_usd
								} /mo`;
							}
							return value.plan_title;
						}
					},
					{
						label: '',
						type: 'Button',
						align: 'right',
						width: '44px',
						Button: ({ row }) => {
							let rowIndex = data.findIndex(r => r === row);

							if (!row.isBench)
								return {
									label: 'Options',
									button: {
										label: 'Options',
										variant: 'ghost',
										slots: {
											default: icon('more-horizontal')
										}
									},
									options: [
										{
											label: 'Visit Site',
											condition: () => row.status === 'Active',
											onClick: () =>
												window.open(`https://${row.name}`, '_blank')
										}
									]
								};
							else
								return {
									label: 'Options',
									button: {
										label: 'Options',
										variant: 'ghost',
										slots: {
											default: icon('more-horizontal')
										}
									},
									options: [
										{
											label: 'View in Desk',
											condition: () => this.$team.doc.is_desk_user,
											onClick: () =>
												window.open(
													`${window.location.protocol}//${window.location.host}/app/bench/${row.name}`,
													'_blank'
												)
										},
										{
											label: 'Show Apps',
											onClick: () => {
												toast.promise(
													this.$releaseGroup.getAppVersions
														.submit({
															bench: row.name
														})
														.then(() => {
															this.showAppVersionDialog = true;
														}),
													{
														loading: 'Fetching apps...',
														success: 'Fetched apps with versions',
														error: 'Failed to fetch apps',
														duration: 1000
													}
												);
											}
										},
										{
											label: 'SSH Access',
											condition: () =>
												row.status === 'Active' && row.hasSSHAcess,
											onClick: () => {
												renderDialog(
													h(SSHCertificateDialog, {
														bench: row,
														releaseGroup: this.$releaseGroup.name
													})
												);
											}
										},
										{
											label: 'Update All Sites',
											condition: () =>
												row.status === 'Active' &&
												rowIndex !== 0 &&
												data[rowIndex + 1]?.name !== 'No sites', // check for empty bench
											onClick: () => {
												confirmDialog({
													title: 'Update All Sites',
													message: `Are you sure you want to update all sites in the bench <b>${row.name}</b> to the latest bench?`,
													primaryAction: {
														label: 'Update',
														variant: 'solid',
														onClick: ({ hide }) => {
															toast.promise(
																this.$resources.updateAllSites.submit({
																	name: row.name
																}),
																{
																	loading: 'Updating sites...',
																	success: () => {
																		hide();
																		return 'Sites updated';
																	},
																	error: 'Failed to update sites',
																	duration: 1000
																}
															);
														}
													}
												});
											}
										},
										{
											label: 'Restart Bench',
											condition: () => row.status === 'Active',
											onClick: () => {
												confirmDialog({
													title: 'Restart Bench',
													message: `Are you sure you want to restart the bench <b>${row.name}</b>?`,
													primaryAction: {
														label: 'Restart',
														variant: 'solid',
														theme: 'red',
														onClick: ({ hide }) => {
															toast.promise(
																this.$resources.restartBench.submit({
																	name: row.name
																}),
																{
																	loading: 'Restarting bench...',
																	success: () => {
																		hide();
																		return 'Bench restarted';
																	},
																	error: 'Failed to restart bench',
																	duration: 1000
																}
															);
														}
													}
												});
											}
										},
										{
											label: 'Rebuild Assets',
											condition: () => row.status === 'Active',
											onClick: () => {
												confirmDialog({
													title: 'Rebuild Assets',
													message: `Are you sure you want to rebuild assets for the bench <b>${row.name}</b>?`,
													primaryAction: {
														label: 'Rebuild',
														variant: 'solid',
														theme: 'red',
														onClick: ({ hide }) => {
															toast.promise(
																this.$resources.rebuildBench.submit({
																	name: row.name
																}),
																{
																	loading: 'Rebuilding assets...',
																	success: () => {
																		hide();
																		return 'Assets rebuilt';
																	},
																	error: 'Failed to rebuild assets',
																	duration: 1000
																}
															);
														}
													}
												});
											}
										}
									]
								};
						}
					}
				],
				route(row) {
					if (!row.isBench && row.name != 'No sites') {
						return { name: 'Site Detail', params: { name: row.name } };
					}
				}
			};
		},
		appVersionOptions() {
			return {
				columns: [
					{
						label: 'App',
						fieldname: 'app'
					},
					{
						label: 'Repo',
						fieldname: 'repository',
						format(value, row) {
							return `${row.repository_owner}/${row.repository}`;
						},
						link: (value, row) => {
							return row.repository_url;
						}
					},
					{
						label: 'Branch',
						fieldname: 'branch',
						type: 'Badge'
					},
					{
						label: 'Commit',
						fieldname: 'hash',
						type: 'Badge',
						format(value, row) {
							return value.slice(0, 7);
						}
					},
					{
						label: 'Tag',
						fieldname: 'tag',
						type: 'Badge'
					}
				],
				data: this.$releaseGroup.getAppVersions.data
			};
		},
		deployedVersions() {
			return this.$releaseGroup.deployedVersions;
		},
		$releaseGroup() {
			return getCachedDocumentResource('Release Group', this.releaseGroup);
		}
	},
	components: { GenericList },
	resources: {
		// TODO: Use bench doctype instead
		// faced infinity api calls when using bench doctype
		restartBench() {
			return {
				url: 'press.api.bench.restart'
			};
		},
		rebuildBench() {
			return {
				url: 'press.api.bench.rebuild'
			};
		},
		updateAllSites() {
			return {
				url: 'press.api.bench.update'
			};
		}
	}
};
</script>
