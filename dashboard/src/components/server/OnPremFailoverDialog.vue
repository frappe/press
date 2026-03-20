<template>
	<Dialog
		:options="{
			title: 'On-Prem Failover Setup',
			size: '3xl',
		}"
		v-model="show"
	>
		<template #body-content>
			<div
				class="flex h-[400px] w-full items-center justify-center"
				v-if="
					this.$resources?.onPremFailoverConfig?.loading && !initialDataFetched
				"
			>
				<div class="flex flex-row items-center gap-2 text-gray-700">
					<Spinner class="w-4" />
					Loading configuration...
				</div>
			</div>
			<div v-else>
				<!-- Status -->
				<div class="flex flex-row justify-between items-center">
					<div class="text-base font-medium text-gray-800">Current Status</div>
					<Button
						variant="subtle"
						theme="red"
						size="sm"
						class="ml-2"
						icon-left="pause"
						v-if="
							appServerStatusFlags &&
							databaseServerStatusFlags &&
							appServerStatusFlags?.setup_completed &&
							databaseServerStatusFlags?.setup_completed
						"
						@click="stopReplication"
						:loading="this.$resources?.stopOnPremReplicationSetup?.loading"
					>
						Stop Replication
					</Button>
				</div>
				<div class="overflow-hidden rounded-md border border-gray-300 mt-2">
					<table class="min-w-full">
						<thead class="bg-surface-gray-2">
							<tr>
								<th
									class="px-4 py-2 text-left text-sm font-medium text-gray-700 border-b"
								></th>
								<th
									class="px-4 py-2 text-left text-sm font-medium text-gray-700 border-b"
								>
									App Server
								</th>
								<th
									class="px-4 py-2 text-left text-sm font-medium text-gray-700 border-b"
								>
									Database Server
								</th>
							</tr>
						</thead>
						<tbody>
							<tr>
								<td>ID</td>
								<td>{{ appServerStatusFlags?.id }}</td>
								<td>{{ databaseServerStatusFlags?.id }}</td>
							</tr>
							<tr>
								<td>Wireguard Setup</td>
								<td>
									{{
										appServerStatusFlags?.wireguard_setup_completed
											? 'Yes'
											: 'No'
									}}
								</td>
								<td>
									{{
										databaseServerStatusFlags?.wireguard_setup_completed
											? 'Yes'
											: 'No'
									}}
								</td>
							</tr>
							<tr>
								<td>On-Prem Reachable</td>
								<td>
									{{
										appServerStatusFlags?.on_prem_server_reachable
											? 'Yes'
											: 'No'
									}}
								</td>
								<td>
									{{
										databaseServerStatusFlags?.on_prem_server_reachable
											? 'Yes'
											: 'No'
									}}
								</td>
							</tr>
							<tr>
								<td>On-Prem SSHable</td>
								<td>
									{{
										appServerStatusFlags?.on_prem_server_sshable ? 'Yes' : 'No'
									}}
								</td>
								<td>
									{{
										databaseServerStatusFlags?.on_prem_server_sshable
											? 'Yes'
											: 'No'
									}}
								</td>
							</tr>
							<tr>
								<td>Replication Setup</td>
								<td>
									{{ appServerStatusFlags?.setup_completed ? 'Yes' : 'No' }}
								</td>
								<td>
									{{
										databaseServerStatusFlags?.setup_completed ? 'Yes' : 'No'
									}}
								</td>
							</tr>
						</tbody>
					</table>
				</div>

				<!-- Setup Guide -->
				<div class="output-container mt-4">
					<div class="flex flex-row items-center gap-1">
						<Button
							:icon="isSetupGuideVisible ? 'chevron-down' : 'chevron-right'"
							variant="ghost"
							@click="toggleSetupGuide"
						></Button>
						<p
							class="cursor-pointer text-gray-700 font-medium"
							@click="toggleSetupGuide"
						>
							On-Prem Server Setup Guide
						</p>
					</div>
					<div
						class="flex flex-col gap-2.5 text-sm m-3"
						v-if="isSetupGuideVisible"
					>
						<!-- Add SSH Key -->
						<div class="flex flex-col gap-2">
							<div class="font-medium text-gray-700">1. Add SSH Keys</div>
							<div class="text-gray-600">
								&nbsp;&nbsp;&nbsp;Add the following authorized keys to your
								on-prem server's
								<b>/root/.ssh/authorized_keys</b>
								file.
							</div>
							<ClickToCopyField :text-content="authorizedKeys" />
						</div>
						<!-- Install necessary tools -->
						<div class="flex flex-col gap-2">
							<div class="font-medium text-gray-700">
								2. Install Necessary Tools
							</div>
							<ClickToCopyField
								text-content="apt update -y
apt install -y wireguard resolvconf rsync gawk curl wget nginx redis-server
command -v docker >/dev/null 2>&1 || curl -fsSL https://get.docker.com | bash
"
							/>
						</div>
						<!-- Configure Wireguard -->
						<div class="flex flex-col gap-2">
							<div class="font-medium text-gray-700">
								3. Update Wireguard Configuration
							</div>
							<div class="text-gray-600">
								&nbsp;&nbsp;&nbsp;Copy and paste the following config at
								<b>/etc/wireguard/wg0.conf</b>
							</div>
							<ClickToCopyField :text-content="wireguardConfig" />
						</div>
						<!-- Start Wireguard Service -->
						<div class="flex flex-col gap-2">
							<div class="font-medium text-gray-700">
								4. Start Wireguard Service
							</div>
							<ClickToCopyField
								text-content="systemctl enable --now wg-quick@wg0"
							/>
						</div>
						<!-- Install Failover Management Service -->
						<div class="flex flex-col gap-2">
							<div class="font-medium text-gray-700">
								5. Setup Failover Management Service
							</div>
							<ClickToCopyField
								text-content="curl -fsSL https://raw.githubusercontent.com/frappe/fc-scripts/refs/heads/develop/press-on-prem-failover.sh -o press-on-prem-failover.sh && chmod +x ./press-on-prem-failover.sh && ./press-on-prem-failover.sh"
							/>
						</div>
						<!-- Trigger Replication Setup -->
						<div class="flex flex-col gap-2">
							<div class="font-medium text-gray-700">
								6. Trigger Replication Setup
							</div>
							<div class="text-gray-600">
								&nbsp;&nbsp;&nbsp;Once the above steps are completed, click the
								button to start the setup.
							</div>
							<div class="px-2 mt-2 w-full">
								<Button
									class="w-full"
									variant="solid"
									@click="
										() => this.$resources?.startOnPremReplicationSetup?.submit()
									"
									:loading="
										this.$resources?.startOnPremReplicationSetup?.loading
									"
									:disabled="
										runningPressJobType ||
										(this.appServerStatusFlags?.setup_completed &&
											this.databaseServerStatusFlags?.setup_completed)
									"
								>
									{{
										runningPressJobType
											? `Running ${runningPressJobType}...`
											: `Start On-Prem
									Replication Setup`
									}}
								</Button>
							</div>
						</div>
					</div>
				</div>

				<!-- Jobs -->
				<div
					class="text-base font-medium text-gray-800 mt-4"
					v-if="jobs && jobs.length"
				>
					Recent Jobs
				</div>
				<div>
					<div
						v-for="job in jobs"
						:key="job.name"
						class="output-container mt-2"
					>
						<div class="flex flex-row items-center justify-between">
							<div class="flex flex-row items-center gap-1">
								<Button
									:icon="
										openedJobSection === job.name
											? 'chevron-down'
											: 'chevron-right'
									"
									variant="ghost"
									@click="
										openedJobSection =
											openedJobSection === job.name ? null : job.name
									"
								></Button>
								<p
									class="cursor-pointer text-gray-700 font-medium"
									@click="
										openedJobSection =
											openedJobSection === job.name ? null : job.name
									"
								>
									{{ job.job_type }}
								</p>
							</div>
							<Badge :label="job.status" />
						</div>
						<div
							class="flex flex-col gap-2.5 text-sm m-3"
							v-if="openedJobSection === job.name"
						>
							<div class="mt-1 mb-1 flex flex-row justify-between w-full px-2">
								<div>
									<div class="text-sm font-medium text-gray-500">Start</div>
									<div class="mt-2 text-sm text-gray-900">
										{{ job.start ? $format.date(job.start, 'lll') : '-' }}
									</div>
								</div>
								<div>
									<div class="text-sm font-medium text-gray-500">End</div>
									<div class="mt-2 text-sm text-gray-900">
										{{ job.end ? $format.date(job.end, 'lll') : '-' }}
									</div>
								</div>
								<div>
									<div class="text-sm font-medium text-gray-500">Duration</div>
									<div class="mt-2 text-sm text-gray-900">
										{{ job.duration ? humanizeDuration(job.duration) : '-' }}
									</div>
								</div>
							</div>
							<JobStep
								v-for="step in steps"
								:step="step"
								:key="step.name"
								v-if="steps"
								:emitToggleEvent="true"
								@toggleStep="
									(step, isOpen) => (openedJobStep = isOpen ? step.name : null)
								"
							/>
						</div>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>
<style scoped>
td {
	@apply px-4 py-2 border-b text-sm text-gray-700;
}

tbody tr:last-child td {
	@apply border-b-0;
}

.output-container {
	@apply rounded border px-2 py-2 text-base text-gray-700;
}
</style>
<script>
import { Button } from 'frappe-ui';
import ClickToCopyField from '../ClickToCopyField.vue';
import { confirmDialog } from '../../utils/components';

import { toast } from 'vue-sonner';
import Badge from '../global/Badge.vue';
import JobStep from '../JobStep.vue';

export default {
	name: 'OnPremFailoverDialog',
	props: {
		appServer: {
			type: String,
			required: true,
		},
	},
	components: {
		ClickToCopyField,
		Badge,
		JobStep,
		Button,
	},
	emits: ['update:show'],
	data() {
		return {
			show: true,
			isSetupGuideVisible: false,
			openedJobSection: null,
			openedJobStep: null,
			initialDataFetched: false,
		};
	},
	resources: {
		onPremFailoverConfig() {
			return {
				url: 'press.api.client.run_doc_method',
				initialData: {},
				makeParams: () => {
					return {
						dt: 'Server',
						dn: this.appServer,
						method: 'generate_on_prem_failover_config',
						args: {},
					};
				},
				onSuccess: () => {
					this.initialDataFetched = true;
					setTimeout(() => {
						this.$resources.onPremFailoverConfig.reload();
					}, 5000);
				},
				auto: true,
			};
		},
		startOnPremReplicationSetup() {
			return {
				url: 'press.api.client.run_doc_method',
				makeParams: () => {
					return {
						dt: 'Server',
						dn: this.appServer,
						method: 'start_on_prem_server_replication',
						args: {},
					};
				},
				onSuccess: () => {
					toast.success('On-Prem Replication Setup Started');
					this.$resources.onPremFailoverConfig.reload();
					this.isSetupGuideVisible = false;
				},
				onError: () => {
					toast.error('Failed to start replication setup. Please try again.');
				},
			};
		},
		stopOnPremReplicationSetup() {
			return {
				url: 'press.api.client.run_doc_method',
				makeParams: () => {
					return {
						dt: 'Server',
						dn: this.appServer,
						method: 'stop_on_prem_server_replication',
						args: {},
					};
				},
				onSuccess: () => {
					toast.success('On-Prem Replication Setup Stopped');
					this.$resources.onPremFailoverConfig.reload();
				},
				onError: () => {
					toast.error('Failed to stop replication setup. Please try again.');
				},
			};
		},
	},
	computed: {
		onPremFailoverConfig() {
			return this.$resources?.onPremFailoverConfig?.data?.message || {};
		},
		statusFlags() {
			return this.onPremFailoverConfig?.status || {};
		},
		appServerStatusFlags() {
			return this.onPremFailoverConfig?.status?.app_server || {};
		},
		databaseServerStatusFlags() {
			return this.onPremFailoverConfig?.status?.db_server || {};
		},
		wireguardConfig() {
			return this.onPremFailoverConfig?.wireguard_config || '';
		},
		authorizedKeys() {
			return this.onPremFailoverConfig?.authorized_ssh_keys || '';
		},
		jobs() {
			return this.onPremFailoverConfig?.jobs || [];
		},
		runningPressJobType() {
			return this.onPremFailoverConfig?.running_press_job_type || null;
		},
		steps() {
			if (!this.openedJobSection) return [];
			const job = this.jobs.find((job) => job.name === this.openedJobSection);
			const steps = job?.steps || [];
			let prepared_steps = [];
			steps.forEach((step) => {
				prepared_steps.push({
					name: step.name,
					title: step.step_name,
					output: step.traceback || step.result || 'No Output',
					status: step.status,
					duration: step.duration
						? this.humanizeDuration(parseInt(step.duration))
						: '',
					stage: null,
					isOpen: step.name === this.openedJobStep,
				});
			});
			return prepared_steps;
		},
	},
	methods: {
		toggleSetupGuide() {
			this.isSetupGuideVisible = !this.isSetupGuideVisible;
		},
		humanizeDuration(seconds) {
			seconds = Math.floor(seconds);

			const h = Math.floor(seconds / 3600);
			const m = Math.floor((seconds % 3600) / 60);
			const s = seconds % 60;

			const parts = [];
			if (h) parts.push(`${h}h`);
			if (m) parts.push(`${m}m`);
			if (s || parts.length === 0) parts.push(`${s}s`);

			return parts.join(' ');
		},
		stopReplication() {
			confirmDialog({
				title: 'Stop Replication Setup',
				message:
					'Are you sure you want to stop the replication setup? The DR Server will stop syncing any new data from the Primary Server.',
				primaryAction: {
					label: 'Stop',
					variant: 'solid',
					theme: 'red',
					onClick: ({ hide }) => {
						return this.$resources?.stopOnPremReplicationSetup
							?.submit()
							.then(() => {
								hide();
							});
					},
				},
			});
		},
	},
};
</script>
