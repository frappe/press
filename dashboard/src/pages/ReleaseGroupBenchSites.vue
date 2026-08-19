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
		<AlertBanner
			:title="`You have ${$resources.inQueueBenches.data.length} bench(es) in queue. Please wait for them to be provisioned.`"
			type="info"
			v-if="$resources.inQueueBenches.data?.length > 0"
		>
			<Button
				class="ml-auto min-w-[7rem]"
				variant="outline"
				link="https://docs.frappe.io/cloud/benches/updating_a_bench#bench-provisioning-amp-queueing"
			>
				Know More
			</Button>
		</AlertBanner>
		<ObjectList class="mt-3" :options="listOptions" />
	</div>
</template>
<script lang="jsx">
import Badge from '@/components/global/Badge.vue';
import { getCachedDocumentResource, Tooltip } from 'frappe-ui';
import BenchActionsDropdown from '../components/BenchActionsDropdown.vue';
import ObjectList from '../components/ObjectList.vue';
import {
	getSitesTabColumns,
	sitesTabRoute,
	siteTabFilterControls,
} from '../objects/common';
import { icon } from '../utils/components';
import DismissableBanner from '../components/DismissableBanner.vue';
import CustomAlerts from '../components/CustomAlerts.vue';

export default {
	name: 'ReleaseGroupBenchSites',
	props: ['releaseGroup', 'actionsAccess'],
	components: { ObjectList, DismissableBanner, CustomAlerts },
	data() {
		return {
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
		inQueueBenches() {
			return {
				type: 'list',
				doctype: 'New Bench Queue',
				filters: {
					group: this.$releaseGroup.name,
					status: 'Queued',
					skip_team_filter_for_system_user_and_support_agent: true,
				},
				fields: ['status', 'group'],
				orderBy: 'creation desc',
				pageLength: 99999,
				auto: true,
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

					const IconHash = icon('hash', 'w-3 h-3');
					const IconStar = icon('star', 'w-3 h-3');
					return (
						<div class="flex items-center">
							<Tooltip text="View bench details">
								<a
									class="text-base font-medium leading-6 text-ink-gray-9 cursor-pointer"
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
										class="p-1 ml-2 text-ink-gray-7 bg-surface-gray-2 rounded"
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
										class="p-1 ml-2 text-ink-gray-7 bg-surface-gray-2 rounded"
										href="https://docs.frappe.io/cloud/in-place-updates"
										target="_blank"
									>
										<IconStar />
									</a>
								</Tooltip>
							)}
							<BenchActionsDropdown
								class="ml-auto"
								bench={bench.name}
								benchRow={bench}
								releaseGroup={this.$releaseGroup.name}
								actionsAccess={this.actionsAccess}
							/>
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
						disabled:
							!this.$resources.benches.data?.length ||
							!this.$resources.benches.data?.some(
								(bench) => bench.status === 'Active',
							) ||
							!this.$releaseGroup.doc?.deploy_information?.last_deploy,
						route: {
							name: 'Release Group New Site',
							params: { bench: this.releaseGroup },
						},
					};
				},
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
	},
};
</script>
