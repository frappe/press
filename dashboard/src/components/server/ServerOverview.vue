<template>
	<div class="w-100" v-if="$appServer?.doc">
		<CustomAlerts ctx_type="Server" :ctx_name="$appServer?.doc?.name" />
		<div class="grid grid-cols-1 items-start gap-5 sm:grid-cols-2">
			<div
				v-for="server in $appServer?.doc?.secondary_server
					? $dbReplicaServer?.doc
						? [
								'Server',
								'App Secondary Server',
								'Database Server',
								'Replication Server',
							]
						: ['Server', 'App Secondary Server', 'Database Server']
					: $dbReplicaServer?.doc
						? ['Server', 'Database Server', 'Replication Server']
						: ['Server', 'Database Server']"
				class="col-span-1 rounded-md border lg:col-span-2"
			>
				<div
					v-if="
						!(
							server === 'Database Server' && $appServer?.doc?.is_unified_server
						)
					"
					class="grid grid-cols-2 lg:grid-cols-4"
					:class="{
						'opacity-70 pointer-events-none':
							server === 'App Secondary Server' && !$appServer?.doc?.scaled_up,
					}"
				>
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
									<div class="flex items-center text-base text-gray-700">
										<span v-if="!$appServer?.doc?.is_unified_server">{{
											d.label
										}}</span>
										<span v-else>Unified Server Plan</span>
										<Badge
											v-if="
												server === 'App Secondary Server' &&
												!$appServer?.doc?.scaled_up
											"
											class="ml-2"
											theme="gray"
											size="sm"
											variant="subtle"
											label="Standby"
										/>
									</div>

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
												<lucide-info class="h-3.5 w-3.5 text-gray-500" />
											</Tooltip>
										</div>
									</div>
								</div>
								<div class="flex flex-col space-y-2">
									<Button
										v-if="
											d.type === 'header' &&
											!$appServer.doc.is_self_hosted &&
											server != 'App Secondary Server'
										"
										@click="showPlanChangeDialog(server)"
										label="Change"
									/>

									<Button
										v-if="
											server === 'Server' &&
											!$appServer?.doc?.scaled_up &&
											$appServer?.doc?.status === 'Active' &&
											$appServer?.doc?.secondary_server
										"
										:disabled="startedScaleUp"
										@click="scaleUp()"
										label="Scale Up"
									/>

									<Button
										v-if="
											server === 'App Secondary Server' &&
											$appServer?.doc?.scaled_up
										"
										:disabled="startedScaleDown"
										@click="scaleDown()"
										label="Scale Down"
									/>
								</div>
							</div>
							<div v-else-if="d.type === 'progress'">
								<div class="flex items-center justify-between space-x-2">
									<div class="text-base text-gray-700">{{ d.label }}</div>
									<div v-if="d.actions" class="flex items-center space-x-2">
										<Badge
											v-if="d.actionRequired"
											theme="red"
											size="sm"
											:label="d.actionRequired"
											variant="subtle"
											ref-for
										/>

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
											<lucide-info class="mt-2 h-4 w-4 text-gray-500" />
										</Tooltip>
									</div>
								</div>
							</div>
							<div v-else-if="d.type === 'info'">
								<div class="flex items-center justify-between">
									<div class="text-base text-gray-700">{{ d.label }}</div>
								</div>
								<div class="mt-1 text-sm text-gray-600">
									{{ d.value }}
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
	</div>
</template>

<script>
import { toast } from 'vue-sonner';
import { h, defineAsyncComponent } from 'vue';
import { getCachedDocumentResource, Progress } from 'frappe-ui';
import { confirmDialog, renderDialog } from '../../utils/components';
import { getToastErrorMessage } from '../../utils/toast';
import ServerLoadAverage from './ServerLoadAverage.vue';
import { getDocResource } from '../../utils/resource';
import { createResource } from 'frappe-ui';
import Badge from '../global/Badge.vue';
import CustomAlerts from '../CustomAlerts.vue';

export default {
	props: ['server'],
	components: {
		Progress,
		Badge,
		ServerLoadAverage,
		ServerPlansDialog,
		StorageBreakdownDialog,
		CustomAlerts,
	},
	data() {
		return {
			startedScaleUp: false,
			startedScaleDown: false,
			autoscaleDiscount: null,
		};
	},
	async mounted() {
		const get = createResource({
			url: 'press.api.server.get_autoscale_discount',
			method: 'GET',
		});

		this.autoscaleDiscount = await get.fetch();
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
		scaleUp() {
			toast.promise(this.$appServer.scaleUp.submit({}), {
				loading: () => {
					this.startedScaleUp = true;
					return 'Starting scale up…';
				},
				success: () => {
					this.startedScaleUp = false;
					this.$router.push({
						path: this.$appServer.name,
						path: 'auto-scale',
					});
					return 'Scale-up started. Please wait a few minutes.';
				},
				error: (e) => {
					this.startedScaleUp = false;
					if (Array.isArray(e.messages)) {
						return e.messages.join(', ');
					}
					return e.message || 'Scale-up failed';
				},
			});
		},
		scaleDown() {
			toast.promise(this.$appServer.scaleDown.submit({}), {
				loading: () => {
					this.startedScaleDown = true;
					return 'Starting scale down…';
				},
				success: () => {
					this.startedScaleDown = false;
					this.$router.push({
						path: this.$appServer.name,
						path: 'auto-scale',
					});
					return 'Scale-down started. Please wait a few minutes.';
				},
				error: (e) => {
					this.startedScaleDown = false;
					if (Array.isArray(e.messages)) {
						return e.messages.join(', ');
					}
					return e.message || 'Scale-down failed';
				},
			});
		},
		currentUsage(serverType) {
			if (!this.$appServer?.doc) return [];
			if (!this.$dbServer?.doc) return [];

			let formatBytes = (v) => this.$format.bytes(v, 0, 2);

			let doc =
				serverType === 'Server'
					? this.$appServer.doc
					: serverType === 'App Secondary Server'
						? this.$appSecondaryServer?.doc
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
			let additionalStorageIncrementRecommendation =
				doc.recommended_storage_increment;
			let price = 0;
			// not using $format.planTitle cuz of manual calculation of add-on storage plan
			let priceField =
				this.$team.doc.currency === 'INR' ? 'price_inr' : 'price_usd';

			let planDescription = '';
			if (!currentPlan?.name) {
				planDescription = 'No plan selected';
			} else if (currentPlan.price_usd > 0) {
				price = currentPlan[priceField];
				if (serverType === 'App Secondary Server') {
					planDescription = this.autoscaleDiscount
						? `${this.$format.userCurrency(
								this.$format.pricePerHour(price) * this.autoscaleDiscount,
							)}/hour`
						: '';
				} else {
					planDescription = `${this.$format.userCurrency(price, 0)}/mo`;
				}
			} else {
				planDescription = currentPlan.plan_title;
			}

			if (
				serverType === 'App Secondary Server' &&
				!this.$appServer?.doc?.scaled_up
			) {
				return [
					{
						label: 'Secondary Application Server Plan',
						value: planDescription,
						type: 'header',
						isPremium: !!currentPlan?.premium,
					},
					{
						label: 'CPU',
						type: 'info',
						value: 'Monitoring disabled for standby secondary server',
					},
					{
						label: 'Memory',
						type: 'info',
						value: 'Monitoring disabled for standby secondary server',
					},
					{
						label: 'Storage',
						type: 'info',
						value: 'Uses primary server storage configuration',
					},
				];
			}

			return [
				{
					label:
						serverType === 'Server'
							? 'Application Server Plan'
							: serverType === 'Database Server'
								? 'Database Server Plan'
								: serverType === 'App Secondary Server'
									? 'Secondary Application Server Plan'
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
					progress_value: currentUsage.vcpu ? currentUsage.vcpu * 100 : 0,
					value: currentPlan
						? `${((currentUsage.vcpu || 0) * 100).toFixed(
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
				...(serverType === 'App Secondary Server'
					? [
							{
								label: 'Storage',
								type: 'info',
								value: 'Uses primary server storage configuration',
							},
						]
					: [
							{
								label: 'Storage',
								type: 'progress',
								actionRequired: additionalStorageIncrementRecommendation
									? 'Low Storage'
									: '',
								progress_value: currentPlan
									? (currentUsage.disk /
											(diskSize ? diskSize : currentPlan.disk)) *
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
										condition: () => doc.provider != 'Hetzner',
										onClick: () => {
											confirmDialog({
												title: 'Increase Storage',
												message: `Enter the disk size you want to increase to the server <b>${
													doc.title || doc.name
												}</b>
									<div class="rounded mt-4 p-2 text-sm text-gray-700 bg-gray-100 border">
									You will be charged at the rate of
									<strong>
										${this.$format.userCurrency(doc.storage_plan[priceField])}/mo
									</strong>
									for each additional GB of storage.
									${
										additionalStorageIncrementRecommendation
											? `<br /> <br />Recommended storage increment: <strong>${additionalStorageIncrementRecommendation} GiB</strong>`
											: ''
									}
									</div>
									<p class="mt-4 text-sm text-gray-700"><strong>Note</strong>: You can increase the storage size of the server only once in 6 hours.
										</div>`,
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
										condition: () => doc.provider != 'Hetzner',
										onClick: () => {
											confirmDialog({
												title: 'Configure Auto Increase Storage',
												message: `<div class="rounded my-4 p-2 prose-sm prose bg-gray-50 border">

									This feature will automatically increases the storage as it reaches over <b>90%</b> of its capacity.

									<br><br>
									With this feature disabled, disk capacity <strong>will not increase automatically</strong> in the event your server approaches or reaches its storage limit.

									<br><br>
									<strong>Note :</strong>

									<ul>
										<li>
											Disabling this feature may result in <strong>service degradation or downtime</strong> if storage is exhausted.
										</li>
										<li>
											Storage can auto increase only once in <strong>6 hours</strong>.
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
																	else if (
																		doc.name === this.$replicationServer.name
																	)
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
										onClick: () => {
											this.showStorageBreakdownDialog(serverType);
										},
									},
								]
									.filter((e) => e.hidden !== true)
									.filter((e) => {
										if (e.condition) {
											return e.condition();
										}
										return true;
									}),
							},
						]),
			];
		},
	},
	computed: {
		serverInformation() {
			return [
				{
					label: 'Hosted on',
					value: `${this.$appServer.doc.provider} - ${this.$appServer.doc.cluster}`,
				},
				{
					label: this.$appServer.doc.is_unified_server
						? 'Server'
						: 'Application Server',
					value: this.$appServer.doc.name,
				},
				{
					label: 'Secondary App Server',
					value: this.$appServer.doc.secondary_server,
				},
				{
					label: 'Database server',
					value: !this.$appServer.doc.is_unified_server
						? this.$appServer.doc.database_server
						: false,
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
		$appSecondaryServer() {
			return getDocResource({
				doctype: 'Server',
				name: this.$appServer.doc.secondary_server,
			});
		},
		$dbServer() {
			// Should mirror the whitelistedMethods in ServerActions.vue
			return getDocResource({
				doctype: 'Database Server',
				name: this.$appServer.doc.database_server,
				whitelistedMethods: {
					changePlan: 'change_plan',
					reboot: 'reboot',
					rename: 'rename',
					enablePerformanceSchema: 'enable_performance_schema',
					disablePerformanceSchema: 'disable_performance_schema',
					enableBinlogIndexing: 'enable_binlog_indexing_service',
					disableBinlogIndexing: 'disable_binlog_indexing_service',
					getMariadbVariables: 'get_mariadb_variables',
					updateInnodbBufferPoolSize: 'update_innodb_buffer_pool_size',
					updateMaxDbConnections: 'update_max_db_connections',
					updateBinlogRetention: 'update_binlog_retention',
					updateBinlogSizeLimit: 'update_binlog_size_limit',
					getBinlogsInfo: 'get_binlogs_info',
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
