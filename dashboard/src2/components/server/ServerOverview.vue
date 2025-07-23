<template>
	<div
		v-if="$appServer?.doc"
		class="grid grid-cols-1 items-start gap-5 sm:grid-cols-2"
	>
		<div
			v-for="server in !!$dbReplicaServer?.doc
				? ['Server', 'Database Server', 'Replication Server']
				: ['Server', 'Database Server']"
			class="col-span-1 rounded-md border lg:col-span-2"
		>
			<div class="grid grid-cols-2 lg:grid-cols-4">
				<template v-for="(d, i) in currentUsage(server)" :key="d.value">
					<div
						class="border-b p-5 lg:border-b-0"
						:class="{ 'border-r': i + 1 != currentUsage(server).length }"
					>
						<div
							v-if="d.type === 'header'"
							class="m-auto flex h-full items-center justify-between"
						>
							<div
								v-if="d.type === 'header'"
								class="mt-2 flex flex-col space-y-2"
							>
								<div class="text-base text-gray-700">{{ d.label }}</div>
								<div class="space-y-1">
									<div class="flex items-center text-base text-gray-900">
										{{ d.value }}
										<Tooltip v-if="d.isPremium" text="Premium Server">
											<!-- this icon isn't available in unplugin package yet -->
											<svg
												xmlns="http://www.w3.org/2000/svg"
												width="24"
												height="24"
												viewBox="0 0 24 24"
												fill="none"
												stroke="currentColor"
												stroke-width="2"
												stroke-linecap="round"
												stroke-linejoin="round"
												class="lucide lucide-circle-parking ml-2 h-4 w-4 text-gray-600"
											>
												<circle cx="12" cy="12" r="10" />
												<path d="M9 17V7h4a3 3 0 0 1 0 6H9" />
											</svg>
										</Tooltip>
									</div>
									<div class="flex space-x-1">
										<div class="text-sm text-gray-600" v-html="d.subValue" />
										<Tooltip v-if="d.help" :text="d.help">
											<i-lucide-info class="h-3.5 w-3.5 text-gray-500" />
										</Tooltip>
									</div>
								</div>
							</div>
							<Button
								v-if="d.type === 'header' && !$appServer.doc.is_self_hosted"
								@click="showPlanChangeDialog(server)"
								label="Change"
							/>
						</div>
						<div v-else-if="d.type === 'progress'">
							<div class="flex items-center justify-between space-x-2">
								<div class="text-base text-gray-700">{{ d.label }}</div>
								<div v-if="d.actions" class="flex space-x-2">
									<Button v-for="action in d.actions || []" v-bind="action" />
								</div>
								<div v-else class="h-8" />
							</div>
							<div class="mt-2">
								<Progress size="md" :value="d.progress_value || 0" />
								<div class="flex space-x-2">
									<div class="mt-2 flex justify-between">
										<div class="text-sm text-gray-600">
											{{ d.value }}
										</div>
									</div>
									<Tooltip v-if="d.help" :text="d.help">
										<i-lucide-info class="mt-2 h-4 w-4 text-gray-500" />
									</Tooltip>
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
import { toast } from 'vue-sonner';
import { h, defineAsyncComponent } from 'vue';
import { getCachedDocumentResource } from 'frappe-ui';
import { confirmDialog, renderDialog } from '../../utils/components';
import { getToastErrorMessage } from '../../utils/toast';
import ServerPlansDialog from './ServerPlansDialog.vue';
import ServerLoadAverage from './ServerLoadAverage.vue';
import StorageBreakdownDialog from './StorageBreakdownDialog.vue';
import { getDocResource } from '../../utils/resource';

export default {
	props: ['server'],
	components: {
		ServerLoadAverage,
		ServerPlansDialog,
		StorageBreakdownDialog,
	},
	methods: {
		showPlanChangeDialog(serverType) {
			let ServerPlansDialog = defineAsyncComponent(
				() => import('./ServerPlansDialog.vue'),
			);
			renderDialog(
				h(ServerPlansDialog, {
					server:
						serverType === 'Server'
							? this.$appServer.name
							: serverType === 'Database Server'
								? this.$dbServer.name
								: serverType === 'Replication Server'
									? this.$dbReplicaServer?.name
									: null,
					serverType,
				}),
			);
		},
		showStorageBreakdownDialog(serverType) {
			let StorageBreakdownDialog = defineAsyncComponent(
				() => import('./StorageBreakdownDialog.vue'),
			);
			renderDialog(
				h(StorageBreakdownDialog, {
					server:
						serverType === 'Server'
							? this.$appServer.name
							: serverType === 'Database Server'
								? this.$dbServer.name
								: serverType === 'Replication Server'
									? this.$dbReplicaServer?.name
									: null,
					serverType,
				}),
			);
		},
		currentUsage(serverType) {
			if (!this.$appServer?.doc) return [];
			if (!this.$dbServer?.doc) return [];

			let formatBytes = (v) => this.$format.bytes(v, 0, 2);

			let doc =
				serverType === 'Server'
					? this.$appServer.doc
					: serverType === 'Database Server'
						? this.$dbServer.doc
						: serverType === 'Replication Server'
							? this.$dbReplicaServer?.doc
							: null;

			if (!doc) return [];

			let currentPlan = doc.current_plan;
			let currentUsage = doc.usage;
			let diskSize = doc.disk_size;
			let additionalStorage = diskSize - (currentPlan?.disk || 0);
			let price = 0;
			// not using $format.planTitle cuz of manual calculation of add-on storage plan
			let priceField =
				this.$team.doc.currency === 'INR' ? 'price_inr' : 'price_usd';

			let planDescription = '';
			if (!currentPlan?.name) {
				planDescription = 'No plan selected';
			} else if (currentPlan.price_usd > 0) {
				price = currentPlan[priceField];
				planDescription = `${this.$format.userCurrency(price, 0)}/mo`;
			} else {
				planDescription = currentPlan.plan_title;
			}

			return [
				{
					label:
						serverType === 'Server'
							? 'Application Server Plan'
							: serverType === 'Database Server'
								? 'Database Server Plan'
								: 'Replication Server Plan',
					value: planDescription,
					subValue:
						additionalStorage > 0
							? `${this.$format.userCurrency(
									doc.storage_plan[priceField] * additionalStorage,
									0,
								)}/mo`
							: '',
					type: 'header',
					isPremium: !!currentPlan?.premium,
					help:
						additionalStorage > 0
							? `Server Plan: ${this.$format.userCurrency(
									currentPlan[priceField],
								)}/mo & Add-on Storage Plan: ${this.$format.userCurrency(
									doc.storage_plan[priceField] * additionalStorage,
								)}/mo`
							: '',
				},
				{
					label: 'CPU',
					type: 'progress',
					progress_value: currentPlan
						? (currentUsage.vcpu / currentPlan.vcpu) * 100
						: 0,
					value: currentPlan
						? `${(((currentUsage.vcpu || 0) / currentPlan.vcpu) * 100).toFixed(
								2,
							)}% of ${currentPlan.vcpu} ${this.$format.plural(
								currentPlan.vcpu,
								'vCPU',
								'vCPUs',
							)}`
						: '0% vCPU',
				},
				{
					label: 'Memory',
					type: 'progress',
					progress_value: currentPlan
						? (currentUsage.memory / currentPlan.memory) * 100
						: 0,
					value: currentPlan
						? `${formatBytes(currentUsage.memory || 0)} of ${formatBytes(
								currentPlan.memory,
							)}`
						: formatBytes(currentUsage.memory || 0),
				},
				{
					label: 'Storage',
					type: 'progress',
					progress_value: currentPlan
						? (currentUsage.disk / (diskSize ? diskSize : currentPlan.disk)) *
							100
						: 0,
					value: currentPlan
						? `${currentUsage.disk || 0} GB of ${
								diskSize ? diskSize : currentPlan.disk
							} GB`
						: `${currentUsage.disk || 0} GB`,
					help:
						diskSize - (currentPlan?.disk || 0) > 0
							? `Add-on storage: ${diskSize - (currentPlan?.disk || 0)} GB`
							: '',
					actions: [
						{
							label: 'Increase Storage',
							icon: 'plus',
							variant: 'ghost',
							onClick: () => {
								confirmDialog({
									title: 'Increase Storage',
									message: `Enter the disk size you want to increase to the server <b>${
										doc.title || doc.name
									}</b><div class="rounded mt-4 p-2 text-sm text-gray-700 bg-gray-100 border">You will be charged at the rate of <b>${this.$format.userCurrency(
										doc.storage_plan[priceField],
									)}/mo</b> for each additional GB of storage.</div><p class="mt-4 text-sm text-gray-700"><strong>Note</strong>: You can increase the storage size of the server only once in 6 hours.</div>`,
									fields: [
										{
											fieldname: 'storage',
											type: 'select',
											default: 50,
											label: 'Storage (GB)',
											variant: 'outline',
											// options from 5 GB to 500 GB in steps of 5 GB
											options: Array.from({ length: 100 }, (_, i) => ({
												label: `${(i + 1) * 5} GB`,
												value: (i + 1) * 5,
											})),
										},
									],
									onSuccess: ({ hide, values }) => {
										toast.promise(
											this.$appServer.increaseDiskSize.submit(
												{
													server: doc.name,
													increment: Number(values.storage),
												},
												{
													onSuccess: () => {
														hide();
														this.$router.push({
															name: 'Server Detail Plays',
															params: { name: this.$appServer.name },
														});
													},
													onError(e) {
														console.error(e);
													},
												},
											),
											{
												loading: 'Increasing disk size...',
												success: 'Disk size is scheduled to increase',
												error: (e) =>
													getToastErrorMessage(
														e,
														'Failed to increase disk size',
													),
											},
										);
									},
								});
							},
						},
						{
							label: 'Configure Auto Increase Storage',
							icon: 'tool',
							variant: 'ghost',
							onClick: () => {
								confirmDialog({
									title: 'Configure Auto Increase Storage',
									message: `<div class="rounded my-4 p-2 text-sm text-gray-700 bg-gray-100 border">

									This feature will automatically increases the storage as it reaches over <b>90%</b> of its capacity.

									<br><br>
									With this feature disabled, disk capacity <strong>will not increase automatically</strong> in the event your server approaches or reaches its storage limit.

									<br><br>
									<strong>Note :</strong>

									<ul>
										<li>
											• Disabling this feature may result in <strong>service degradation or downtime</strong> if storage is exhausted.
										</li>
										<li>
											• Storage can auto increase only once in <strong>6 hours</strong>.
										</li>
									</ul>
`,
									fields: [
										{
											fieldname: 'auto_increase_storage',
											type: 'checkbox',
											default: doc.auto_increase_storage,
											label: 'Enable Auto Increase Storage',
											variant: 'outline',
										},
										{
											fieldname: 'min',
											type: 'select',
											default: String(doc.auto_add_storage_min),
											label: 'Minimum Storage Increase (GB)',
											variant: 'outline',
											// options from 5 GB to 250 GB in steps of 5 GB
											options: Array.from({ length: 51 }, (_, i) => ({
												label: `${i * 5} GB`,
												value: i * 5,
											})),
											condition: (values) => {
												return values.auto_increase_storage;
											},
										},
										{
											fieldname: 'max',
											type: 'select',
											default: String(doc.auto_add_storage_max),
											label: 'Maximum Storage Increase (GB)',
											variant: 'outline',
											// options from 5 GB to 250 GB in steps of 5 GB
											options: Array.from({ length: 51 }, (_, i) => ({
												label: `${i * 5} GB`,
												value: i * 5,
											})),
											condition: (values) => {
												return values.auto_increase_storage;
											},
										},
									],
									onSuccess: ({ hide, values }) => {
										toast.promise(
											this.$appServer.configureAutoAddStorage.submit(
												{
													server: doc.name,
													enabled: values.auto_increase_storage,
													min: Number(values.min),
													max: Number(values.max),
												},
												{
													onSuccess: () => {
														hide();

														if (doc.name === this.$appServer.name)
															this.$appServer.reload();
														else if (doc.name === this.$dbServer.name)
															this.$dbServer.reload();
														else if (doc.name === this.$replicationServer.name)
															this.$replicationServer.reload();
													},
												},
											),
											{
												loading: 'Configuring auto increase storage...',
												success: 'Auto increase storage is configured',
												error: (err) => {
													return err.messages.length
														? err.messages.join('/n')
														: err.message ||
																'Failed to configure auto increase storage';
												},
											},
										);
									},
								});
							},
						},
						{
							label: 'Storage Breakdown',
							icon: 'pie-chart',
							variant: 'ghost',
							hidden: serverType !== 'Database Server',
							onClick: () => {
								this.showStorageBreakdownDialog(serverType);
							},
						},
					].filter((e) => e.hidden !== true),
				},
			];
		},
	},
	computed: {
		serverInformation() {
			return [
				{
					label: 'Application server',
					value: this.$appServer.doc.name,
				},
				{
					label: 'Database server',
					value: this.$appServer.doc.database_server,
				},
				{
					label: 'Replication server',
					value: this.$appServer.doc.replication_server,
				},
				{
					label: 'Owned by',
					value: this.$appServer.doc.owner_email || this.$appServer.doc.team,
				},
				{
					label: 'Created by',
					value: this.$appServer.doc.owner,
				},
				{
					label: 'Created on',
					value: this.$format.date(this.$appServer.doc.creation),
				},
			].filter((d) => d.value);
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
					rename: 'rename',
				},
			});
		},
		$dbReplicaServer() {
			return getDocResource({
				doctype: 'Database Server',
				name: this.$appServer.doc.replication_server,
				whitelistedMethods: {
					changePlan: 'change_plan',
					reboot: 'reboot',
					rename: 'rename',
				},
			});
		},
	},
};
</script>
