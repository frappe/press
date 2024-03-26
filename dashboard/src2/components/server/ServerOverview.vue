<template>
	<div
		v-if="$appServer?.doc"
		class="grid grid-cols-1 items-start gap-5 sm:grid-cols-2"
	>
		<div
			v-for="server in ['Server', 'Database Server']"
			class="col-span-1 rounded-md border lg:col-span-2"
		>
			<div class="grid grid-cols-2 lg:grid-cols-4">
				<template v-for="(d, i) in currentUsage(server)" :key="d.value">
					<div
						class="border-b p-5 lg:border-b-0"
						:class="{ 'border-r': i + 1 != currentUsage(server).length }"
					>
						<div
							v-if="d.type === 'info'"
							class="flex items-center justify-between"
						>
							<div
								v-if="d.type === 'info'"
								class="mt-2 flex flex-col space-y-2"
							>
								<div class="text-base text-gray-700">{{ d.label }}</div>
								<div>
									<div class="text-base text-gray-900">
										{{ d.value }}
									</div>
								</div>
							</div>
							<Button
								v-if="d.type === 'info'"
								@click="showPlanChangeDialog(server)"
								label="Change"
							/>
						</div>
						<div v-else-if="d.type === 'progress'">
							<div class="text-base text-gray-700">{{ d.label }}</div>
							<div class="mt-2">
								<Progress size="md" :value="d.progress_value" />
								<div>
									<div class="mt-2 flex justify-between">
										<div class="text-sm text-gray-600">
											{{ d.value }}
										</div>
									</div>
								</div>
							</div>
						</div>
					</div>
				</template>
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

		<ServerLoadAverage :server="server" />
	</div>
</template>

<script>
import { h, defineAsyncComponent } from 'vue';
import { getCachedDocumentResource } from 'frappe-ui';
import { renderDialog } from '../../utils/components';
import ServerPlansDialog from './ServerPlansDialog.vue';
import ServerLoadAverage from './ServerLoadAverage.vue';
import { getDocResource } from '../../utils/resource';

export default {
	props: ['server'],
	components: {
		ServerLoadAverage,
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
		currentUsage(serverType) {
			if (!this.$appServer.doc) return [];
			if (!this.$dbServer.doc) return [];

			let formatBytes = v => this.$format.bytes(v, 0, 2);

			let currentPlan =
				serverType === 'Server'
					? this.$appServer.doc.current_plan
					: this.$dbServer.doc.current_plan;
			let currentUsage =
				serverType === 'Server'
					? this.$appServer.doc.usage
					: this.$dbServer.doc.usage;

			let diskSize =
				serverType === 'Server'
					? this.$appServer.doc.disk_size
					: this.$dbServer.doc.disk_size;

			let planDescription = '';
			if (currentPlan.price_usd > 0) {
				if (this.$team.doc.currency === 'INR') {
					planDescription = `₹${currentPlan.price_inr} /month`;
				} else {
					planDescription = `$${currentPlan.price_usd} /month`;
				}
			} else {
				planDescription = currentPlan.plan_title;
			}

			return [
				{
					label:
						serverType === 'Server'
							? 'Application Server Plan'
							: 'Database Server Plan',
					value: planDescription,
					type: 'info'
				},
				{
					label: 'CPU',
					type: 'progress',
					progress_value: (currentUsage.vcpu / currentPlan.vcpu) * 100,
					value: `${currentUsage.vcpu || 0} vCPU / ${
						currentPlan.vcpu
					} ${this.$format.plural(currentPlan.vcpu, 'vCPU', 'vCPUs')}`
				},
				{
					label: 'Memory',
					type: 'progress',
					progress_value: (currentUsage.memory / currentPlan.memory) * 100,
					value: `${formatBytes(currentUsage.memory || 0)} / ${formatBytes(
						currentPlan.memory
					)}`
				},
				{
					label: 'Storage',
					type: 'progress',
					progress_value:
						(currentUsage.disk / (diskSize ? diskSize : currentPlan.disk)) *
						100,
					value: `${currentUsage.disk || 0} GB / ${
						diskSize ? diskSize : currentPlan.disk
					} GB`
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
