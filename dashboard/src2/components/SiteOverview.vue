<template>
	<div
		v-if="$site?.doc"
		class="grid grid-cols-1 items-start gap-5 sm:grid-cols-2"
	>
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
					<div class="w-1/3 text-base text-gray-700">{{ d.label }}</div>
					<div class="w-2/3 text-base font-medium">{{ d.value }}</div>
				</div>
			</div>
		</div>
		<div class="mt- rounded-md border">
			<div class="flex h-12 items-center justify-between border-b px-5">
				<h2 class="text-lg font-medium text-gray-900">Plan</h2>
				<Button @click="showPlanChangeDialog">Change</Button>
			</div>
			<div class="">
				<div
					v-for="d in current_usage"
					:key="d.label"
					class="flex items-center px-5 py-3 last:pb-5 even:bg-gray-50/70"
				>
					<div class="w-1/3 text-base text-gray-700">{{ d.label }}</div>
					<div class="w-2/3 text-base font-medium">
						{{ d.value }}
					</div>
				</div>
			</div>
		</div>
	</div>
</template>
<script>
import { h, defineAsyncComponent } from 'vue';
import { getCachedDocumentResource } from 'frappe-ui';
import LucideGaugeCircle from '~icons/lucide/gauge-circle.vue';
import LucideHardDrive from '~icons/lucide/hard-drive.vue';
import LucideDatabase from '~icons/lucide/database.vue';
import { renderDialog } from '../utils/components';

export default {
	name: 'SiteOverview',
	props: ['site'],
	methods: {
		showPlanChangeDialog() {
			let SitePlansDialog = defineAsyncComponent(() =>
				import('../components/ManageSitePlansDialog.vue')
			);
			renderDialog(h(SitePlansDialog, { site: this.site }));
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
					value: this.$site.doc.team
				},
				{
					label: 'Created by',
					value: this.$site.doc.owner
				},
				{
					label: 'Created on',
					value: this.$site.doc.creation
				},
				{
					label: 'Last updated',
					value: this.$site.doc.last_updated
				}
			];
		},
		current_usage() {
			let formatBytes = v => this.$format.bytes(v, 0, 2);
			let currentPlan = this.$site.doc.current_plan;
			let planDescription = '';
			if (currentPlan.price_usd > 0) {
				if (this.$team.doc.currency === 'INR') {
					planDescription = `₹${currentPlan.price_inr} /month (₹${currentPlan.price_per_day_inr} /day)`;
				} else {
					planDescription = `$${currentPlan.price_usd} /month ($${currentPlan.price_per_day_usd} /day)`;
				}
			} else {
				planDescription = currentPlan.plan_title;
			}

			return [
				{
					label: 'Current Plan',
					icon: LucideGaugeCircle,
					value: planDescription
				},
				{
					label: 'CPU Usage',
					icon: LucideGaugeCircle,
					value: `${this.$site.doc.current_usage.cpu} / ${
						this.$site.doc.current_plan.cpu_time_per_day
					} ${this.$format.plural(
						this.$site.doc.current_plan.cpu_time_per_day,
						'hour',
						'hours'
					)}`
				},
				{
					label: 'Storage Usage',
					icon: LucideHardDrive,
					value: `${formatBytes(
						this.$site.doc.current_usage.storage
					)} / ${formatBytes(this.$site.doc.current_plan.max_storage_usage)}`
				},
				{
					label: 'Database Usage',
					icon: LucideDatabase,
					value: `${formatBytes(
						this.$site.doc.current_usage.database
					)} / ${formatBytes(this.$site.doc.current_plan.max_database_usage)}`
				}
			];
		},
		$site() {
			return getCachedDocumentResource('Site', this.site);
		}
	}
};
</script>
