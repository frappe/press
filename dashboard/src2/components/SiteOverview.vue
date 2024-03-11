<template>
	<div
		v-if="$site?.doc"
		class="grid grid-cols-1 items-start gap-5 lg:grid-cols-2"
	>
		<div class="col-span-1 rounded-md border lg:col-span-2">
			<div class="grid grid-cols-2 lg:grid-cols-4">
				<div class="border-b border-r p-5 lg:border-b-0">
					<div class="text-base text-gray-700">Current Plan</div>
					<div class="mt-2 flex items-start justify-between">
						<div>
							<div class="leading-4">
								<span class="text-base text-gray-900" v-if="currentPlan">
									{{ $format.planTitle(currentPlan) }}
									<span v-if="currentPlan.price_inr">/ month</span>
								</span>
								<span class="text-base text-gray-900" v-else>
									No plan set
								</span>
							</div>
							<div
								class="mt-1 text-sm leading-3 text-gray-600"
								v-if="currentPlan"
							>
								{{
									currentPlan.support_included
										? 'Support included'
										: 'Support not included'
								}}
							</div>
						</div>
						<Button @click="showPlanChangeDialog">Change</Button>
					</div>
				</div>
				<div class="border-b p-5 lg:border-b-0 lg:border-r">
					<div class="text-base text-gray-700">Compute</div>
					<div class="mt-2">
						<Progress
							size="md"
							:value="
								currentPlan
									? (currentUsage.cpu / currentPlan.cpu_time_per_day) * 100
									: 0
							"
						/>
						<div>
							<div class="mt-2 flex justify-between">
								<div class="text-sm text-gray-600">
									{{ currentUsage.cpu }}
									{{ $format.plural(currentUsage.cpu, 'hour', 'hours') }}
									<template v-if="currentPlan">
										of {{ currentPlan?.cpu_time_per_day }} hours
									</template>
								</div>
							</div>
						</div>
					</div>
				</div>
				<div class="border-r p-5">
					<div class="text-base text-gray-700">Storage</div>
					<div class="mt-2">
						<Progress
							size="md"
							:value="
								currentPlan
									? (currentUsage.storage / currentPlan.max_storage_usage) * 100
									: 0
							"
						/>
						<div>
							<div class="mt-2 flex justify-between">
								<div class="text-sm text-gray-600">
									{{ formatBytes(currentUsage.storage) }}
									<template v-if="currentPlan">
										of {{ formatBytes(currentPlan.max_storage_usage) }}
									</template>
								</div>
							</div>
						</div>
					</div>
				</div>
				<div class="p-5">
					<div class="text-base text-gray-700">Database</div>
					<div class="mt-2">
						<Progress
							size="md"
							:value="
								currentPlan
									? (currentUsage.database / currentPlan.max_database_usage) *
									  100
									: 0
							"
						/>
						<div>
							<div class="mt-2 flex justify-between">
								<div class="text-sm text-gray-600">
									{{ formatBytes(currentUsage.database) }}
									<template v-if="currentPlan">
										of
										{{ formatBytes(currentPlan.max_database_usage) }}
									</template>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
		<div class="rounded-md border">
			<div class="h-12 border-b px-5 py-4">
				<h2 class="text-lg font-medium text-gray-900">Site information</h2>
			</div>
			<div>
				<div
					v-for="d in siteInformation"
					:key="d.label"
					class="flex items-center px-5 py-3 last:pb-5 even:bg-gray-50/70"
				>
					<div class="w-1/3 text-base text-gray-600">{{ d.label }}</div>
					<div class="w-2/3 text-base text-gray-900">
						{{ d.value }}
					</div>
				</div>
			</div>
		</div>
		<SiteDailyUsage :site="site" />
	</div>
</template>
<script>
import { h, defineAsyncComponent } from 'vue';
import { getCachedDocumentResource, Progress } from 'frappe-ui';
import { renderDialog } from '../utils/components';
import SiteDailyUsage from './SiteDailyUsage.vue';

export default {
	name: 'SiteOverview',
	props: ['site'],
	components: { SiteDailyUsage, Progress },
	methods: {
		showPlanChangeDialog() {
			let SitePlansDialog = defineAsyncComponent(() =>
				import('../components/ManageSitePlansDialog.vue')
			);
			renderDialog(h(SitePlansDialog, { site: this.site }));
		},
		formatBytes(v) {
			return this.$format.bytes(v, 0, 2);
		}
	},
	computed: {
		siteInformation() {
			return [
				{
					label: 'Site name',
					value: this.$site.doc.name
				},
				{
					label: 'Owned by',
					value: this.$site.doc.owner_email
				},
				{
					label: 'Created by',
					value: this.$site.doc.owner
				},
				{
					label: 'Created on',
					value: this.$format.date(this.$site.doc.creation)
				},
				{
					label: 'Last updated',
					value: this.$format.date(this.$site.doc.last_updated) || 'Never'
				}
			];
		},
		currentPlan() {
			if (!this.$site.doc.current_plan) return null;
			let currency = this.$team.doc.currency;
			return {
				price:
					currency === 'INR'
						? this.$site.doc.current_plan.price_inr
						: this.$site.doc.current_plan.price_usd,
				price_per_day:
					currency === 'INR'
						? this.$site.doc.current_plan.price_per_day_inr
						: this.$site.doc.current_plan.price_per_day_usd,
				currency: currency == 'INR' ? '₹' : '$',
				...this.$site.doc.current_plan
			};
		},
		currentUsage() {
			return this.$site.doc.current_usage;
		},
		$site() {
			return getCachedDocumentResource('Site', this.site);
		}
	}
};
</script>
