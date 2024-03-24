<template>
	<div>
		<ObjectList class="mt-3" :options="listOptions" />
		<div class="px-2 py-2 text-right">
			<Button
				v-if="$resources.sites.hasNextPage"
				@click="$resources.sites.next()"
				:loading="$resources.sites.loading"
			>
				Load more
			</Button>
		</div>
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
<script lang="jsx">
import { defineAsyncComponent, h } from 'vue';
import {
	getCachedDocumentResource,
	Tooltip,
	createDocumentResource
} from 'frappe-ui';
import GenericList from '../components/GenericList.vue';
import ObjectList from '../components/ObjectList.vue';
import Badge from '@/components/global/Badge.vue';
import SSHCertificateDialog from '../components/bench/SSHCertificateDialog.vue';
import { confirmDialog, icon, renderDialog } from '../utils/components';
import { toast } from 'vue-sonner';
import { trialDays } from '../utils/site';
import { getTeam } from '../data/team';
import { userCurrency } from '../utils/format';
import ActionButton from '../components/ActionButton.vue';

export default {
	name: 'ReleaseGroupBenchSites',
	props: ['releaseGroup'],
	components: { GenericList, ObjectList },
	data() {
		return {
			showAppVersionDialog: false,
			sitesGroupedByBench: []
		};
	},
	resources: {
		benches() {
			return {
				type: 'list',
				doctype: 'Bench',
				filters: {
					group: this.$releaseGroup.name
				},
				fields: ['name', 'status'],
				orderBy: 'creation desc',
				pageLength: 99999,
				auto: true
			};
		},
		sites() {
			return {
				type: 'list',
				doctype: 'Site',
				filters: {
					group: this.$releaseGroup.name,
					skip_team_filter_for_system_user: true
				},
				fields: [
					'name',
					'status',
					'bench',
					'plan.plan_title as plan_title',
					'plan.price_usd as price_usd',
					'plan.price_inr as price_inr',
					'cluster.image as cluster_image',
					'cluster.title as cluster_title'
				],
				orderBy: 'creation desc',
				pageLength: 50,
				transform(data) {
					return this.groupSitesByBench(data);
				}
			};
		}
	},
	computed: {
		listOptions() {
			return {
				list: this.$resources.sites,
				groupHeader: ({ group }) => {
					let options = this.benchOptions(group);
					let IconHash = icon('hash', 'w-3 h-3');
					return (
						<div class="flex items-center">
							<div class="text-base font-medium leading-6 text-gray-900">
								{group.group}
							</div>
							<Badge class="ml-4" label={group.status} />
							{group.has_app_patch_applied && (
								<Tooltip
									text="Apps in this deploy have been patched"
									placement="top"
								>
									<div class="ml-2 rounded bg-gray-100 p-1 text-gray-700">
										<IconHash />
									</div>
								</Tooltip>
							)}
							<ActionButton class="ml-auto" options={options} />
						</div>
					);
				},
				searchField: 'name',
				columns: [
					{
						label: 'Site Name',
						fieldname: 'name',
						prefix() {
							return h('div', { class: 'ml-2 w-3.5 h-3.5' });
						}
					},
					{
						label: 'Status',
						fieldname: 'status',
						type: 'Badge'
					},
					{
						label: 'Region',
						fieldname: 'cluster_title',
						prefix(row) {
							if (row.cluster_title)
								return h('img', {
									src: row.cluster_image,
									class: 'w-4 h-4',
									alt: row.cluster_title
								});
						}
					},
					{
						label: 'Plan',
						format(value, row) {
							if (row.trial_end_date) {
								return trialDays(row.trial_end_date);
							}
							let $team = getTeam();
							if (row.price_usd > 0) {
								let india = $team.doc.country == 'India';
								let formattedValue = userCurrency(
									india ? row.price_inr : row.price_usd,
									0
								);
								return `${formattedValue} /mo`;
							}
							return row.plan_title;
						}
					}
				],
				route(row) {
					return { name: 'Site Detail', params: { name: row.name } };
				},
				primaryAction: () => {
					return {
						label: 'New Site',
						slots: {
							prefix: icon('plus', 'w-4 h-4')
						},
						route: {
							name: 'Bench New Site',
							params: { bench: this.releaseGroup }
						}
					};
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
						},
						link: (value, row) => {
							return `https://github.com/${row.repository_owner}/${row.repository}/commit/${value}`;
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
		$releaseGroup() {
			return getCachedDocumentResource('Release Group', this.releaseGroup);
		}
	},
	methods: {
		groupSitesByBench(data) {
			if (!this.$resources.benches.data) return [];
			return this.$resources.benches.data.map(bench => {
				let sites = (data || []).filter(site => site.bench === bench.name);
				return {
					...bench,
					collapsed: false,
					group: bench.name,
					rows: sites
				};
			});
		},
		benchOptions(bench) {
			return [
				{
					label: 'View in Desk',
					condition: () => this.$team.doc.is_desk_user,
					onClick: () =>
						window.open(
							`${window.location.protocol}//${window.location.host}/app/bench/${bench.name}`,
							'_blank'
						)
				},
				{
					label: 'Show Apps',
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
								duration: 1000
							}
						);
					}
				},
				{
					label: 'SSH Access',
					condition: () => bench.status === 'Active',
					onClick: () => {
						renderDialog(
							h(SSHCertificateDialog, {
								bench: bench.name,
								releaseGroup: this.$releaseGroup.name
							})
						);
					}
				},
				{
					label: 'View Logs',
					condition: () => bench.status === 'Active',
					onClick: () => {
						let BenchLogsDialog = defineAsyncComponent(() =>
							import('../components/bench/BenchLogsDialog.vue')
						);

						renderDialog(
							h(BenchLogsDialog, {
								bench: bench.name
							})
						);
					}
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
										this.$bench(bench.name).updateAllSites.submit(),
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
									toast.promise(this.$bench(bench.name).restart.submit(), {
										loading: 'Restarting bench...',
										success: () => {
											hide();
											return 'Bench restarted';
										},
										error: 'Failed to restart bench',
										duration: 1000
									});
								}
							}
						});
					}
				},
				{
					label: 'Rebuild Assets',
					condition: () =>
						bench.status === 'Active' &&
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
									toast.promise(this.$bench(bench.name).rebuild.submit(), {
										loading: 'Rebuilding assets...',
										success: () => {
											hide();
											return 'Assets will be rebuilt in the background. This may take a few minutes.';
										},
										error: 'Failed to rebuild assets',
										duration: 1000
									});
								}
							}
						});
					}
				}
			];
		},
		$bench(name) {
			let $bench = createDocumentResource({
				doctype: 'Bench',
				name: name,
				whitelistedMethods: {
					restart: 'restart',
					rebuild: 'rebuild',
					updateAllSites: 'update_all_sites'
				},
				auto: false
			});
			return $bench;
		}
	}
};
</script>
