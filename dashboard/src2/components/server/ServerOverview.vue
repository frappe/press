<template>
	<div
		v-if="$server?.doc"
		class="grid grid-cols-1 items-start gap-5 sm:grid-cols-2"
	>
		<div class="rounded-md border">
			<div class="h-12 border-b px-5 py-4">
				<h2 class="text-lg font-medium text-gray-900">Server Information</h2>
			</div>
			<div>
				<div
					v-for="d in serverInformation"
					:key="d.label"
					class="flex items-center px-5 py-3 last:pb-5 even:bg-gray-50/70"
				>
					<div class="w-1/3 text-base text-gray-700">{{ d.label }}</div>
					<div class="w-2/3 text-base font-medium">{{ d.value }}</div>
				</div>
			</div>
		</div>
		<div class="rounded-md border">
			<div class="flex h-12 items-center justify-between border-b px-5">
				<h2 class="text-lg font-medium text-gray-900">Plan</h2>
				<Button @click="showPlanChangeDialog"> Change </Button>
			</div>
			<div v-if="$server.doc.current_plan">
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
			<div v-else class="flex items-center justify-center p-3">
				<div class="text-base text-gray-700">No Plan Selected</div>
			</div>
		</div>
	</div>
</template>

<script>
import { h, defineAsyncComponent } from 'vue';
import { getCachedDocumentResource } from 'frappe-ui';
import { renderDialog } from '../../utils/components';
import ServerPlansDialog from './ServerPlansDialog.vue';

export default {
	props: ['server', 'serverType'],
	components: {
		ServerPlansDialog
	},
	methods: {
		showPlanChangeDialog() {
			let ServerPlansDialog = defineAsyncComponent(() =>
				import('./ServerPlansDialog.vue')
			);
			renderDialog(
				h(ServerPlansDialog, {
					server: this.server,
					serverType: this.serverType
				})
			);
		}
	},
	computed: {
		serverInformation() {
			return [
				{
					label: 'Server title',
					value: this.$server.doc.title,
					condition: () => this.$server.doc.title
				},
				{
					label: 'Server name',
					value: this.$server.doc.name
				},
				{
					label: 'Owned by',
					value: this.$server.doc.team
				},
				{
					label: 'Created by',
					value: this.$server.doc.owner
				},
				{
					label: 'Created on',
					value: this.$format.date(this.$server.doc.creation)
				}
			].filter(d => !d.condition || d.condition());
		},
		current_usage() {
			let formatBytes = v => this.$format.bytes(v, 0, 2);
			let currentPlan = this.$server.doc.current_plan;
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
					value: planDescription
				},
				{
					label: 'CPU',
					value: `${this.$server.doc.usage.vcpu || 0} vCPU / ${
						currentPlan.vcpu
					} ${this.$format.plural(currentPlan.vcpu, 'vCPU', 'vCPUs')}`
				},
				{
					label: 'Memory',
					value: `${formatBytes(
						this.$server.doc.usage.memory || 0
					)} / ${formatBytes(currentPlan.memory)}`
				},
				{
					label: 'Storage',
					value: `${formatBytes(
						this.$server.doc.usage.disk || 0
					)} / ${formatBytes(currentPlan.disk)}`
				}
			];
		},
		$server() {
			return getCachedDocumentResource(this.serverType, this.server);
		}
	}
};
</script>
