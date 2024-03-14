<template>
	<div
		v-if="$appServer?.doc"
		class="grid grid-cols-1 items-start gap-5 sm:grid-cols-2"
	>
		<div class="flex flex-col space-y-4">
			<div class="rounded-md border">
				<div class="flex h-12 items-center justify-between border-b px-5">
					<h2 class="text-lg font-medium text-gray-900">
						Application Server Plan
					</h2>
					<Button @click="showPlanChangeDialog('Server')"> Change </Button>
				</div>
				<div v-if="$appServer.doc.current_plan">
					<div
						v-for="d in current_usage('Server')"
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
			<div class="rounded-md border">
				<div class="flex h-12 items-center justify-between border-b px-5">
					<h2 class="text-lg font-medium text-gray-900">
						Database Server Plan
					</h2>
					<Button @click="showPlanChangeDialog('Database Server')">
						Change
					</Button>
				</div>
				<div v-if="$dbServer.doc?.current_plan">
					<div
						v-for="d in current_usage('Database Server')"
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
	</div>
</template>

<script>
import { h, defineAsyncComponent } from 'vue';
import { getCachedDocumentResource } from 'frappe-ui';
import { renderDialog } from '../../utils/components';
import ServerPlansDialog from './ServerPlansDialog.vue';
import { getDocResource } from '../../utils/resource';

export default {
	props: ['server'],
	components: {
		ServerPlansDialog
	},
	methods: {
		showPlanChangeDialog(serverType) {
			let ServerPlansDialog = defineAsyncComponent(() =>
				import('./ServerPlansDialog.vue')
			);
			renderDialog(
				h(ServerPlansDialog, {
					server:
						serverType === 'Server'
							? this.$appServer.doc.name
							: this.$dbServer.doc.name,
					serverType
				})
			);
		},
		current_usage(serverType) {
			let formatBytes = v => this.$format.bytes(v, 0, 2);

			let currentPlan =
				serverType === 'Server'
					? this.$appServer.doc.current_plan
					: this.$dbServer.doc.current_plan;
			let currentUsage =
				serverType === 'Server'
					? this.$appServer.doc.usage
					: this.$dbServer.doc.usage;

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
					value: `${currentUsage.vcpu || 0} vCPU / ${
						currentPlan.vcpu
					} ${this.$format.plural(currentPlan.vcpu, 'vCPU', 'vCPUs')}`
				},
				{
					label: 'Memory',
					value: `${formatBytes(currentUsage.memory || 0)} / ${formatBytes(
						currentPlan.memory
					)}`
				},
				{
					label: 'Storage',
					value: `${formatBytes(currentUsage.disk || 0)} / ${formatBytes(
						currentPlan.disk
					)}`
				}
			];
		}
	},
	computed: {
		serverInformation() {
			return [
				{
					label: 'Application server',
					value: this.$appServer.doc.name
				},
				{
					label: 'Database server',
					value: this.$appServer.doc.database_server
				},
				{
					label: 'Owned by',
					value: this.$appServer.doc.team
				},
				{
					label: 'Created by',
					value: this.$appServer.doc.owner
				},
				{
					label: 'Created on',
					value: this.$format.date(this.$appServer.doc.creation)
				}
			];
		},
		$appServer() {
			return getCachedDocumentResource('Server', this.server);
		},
		$dbServer() {
			return getDocResource({
				doctype: 'Database Server',
				name: this.$appServer.doc.database_server,
				whitelistedMethods: {
					changePlan: 'change_plan',
					reboot: 'reboot',
					rename: 'rename'
				}
			});
		}
	}
};
</script>
