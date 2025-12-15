<template>
	<Dialog
		v-model="show"
		@close="resetValues"
		:options="{ title: 'Resize Virtual Disk' }"
	>
		<template #body-content>
			<div class="space-y-4">
				<p class="text-base">Select a server to shrink its disk size</p>

				<FormControl
					label="Select Server"
					type="select"
					v-model="selectedServer"
					:options="serverTypeOptions"
					placeholder="Choose a server"
				/>

				<div
					v-if="
						selectedServer && currentVolumes.length === 0 && !isLoadingVolumes
					"
					class="flex items-center rounded bg-red-50 p-4 text-sm text-red-700"
				>
					<lucide-alert-circle class="mr-2 h-4 w-4" />
					No volumes to shrink found for this server.
				</div>

				<template v-if="selectedServer && currentVolumes.length > 0">
					<div
						class="flex items-center rounded bg-yellow-50 p-4 text-sm text-yellow-700"
					>
						<lucide-alert-triangle class="mr-2 h-4 w-4" />
						<span
							><b>Warning:</b> Resizing the disk will cause server downtime
							during the operation.</span
						>
					</div>

					<FormControl
						label="Select Volume"
						type="select"
						v-model="selectedVolume"
						:options="volumeOptions"
						placeholder="Choose a volume"
					/>

					<FormControl
						v-if="selectedVolume"
						label="Expected Volume Size (GB)"
						type="number"
						v-model="expectedVolumeSize"
						:min="1"
						:step="1"
						placeholder="Enter size in GB"
					/>

					<div
						v-if="expectedVolumeSize && expectedVolumeSize >= currentVolumeSize"
						class="flex items-center rounded bg-yellow-50 p-4 text-sm text-yellow-700"
					>
						<lucide-alert-triangle class="mr-2 h-4 w-4" />
						New volume size must be less than current size ({{
							currentVolumeSize
						}}
						GB).
					</div>

					<DateTimeControl
						v-if="selectedVolume"
						v-model="targetDateTime"
						label="Schedule Time"
					/>
				</template>
			</div>
		</template>
		<template #actions>
			<Button
				class="w-full"
				variant="solid"
				label="Resize Disk"
				:disabled="isResizeDisabled"
				:loading="$resources.virtualDiskResize?.loading"
				@click="resizeDisk"
			/>
		</template>
	</Dialog>
</template>

<script>
import { toast } from 'vue-sonner';
import DateTimeControl from '../DateTimeControl.vue';

export default {
	name: 'ServerDiskResizeDialog',
	props: {
		servers: {
			type: Object,
			required: true,
		},
		onDiskResizeCreation: {
			type: Function,
			default: () => {},
		},
	},
	components: { DateTimeControl },
	data() {
		return {
			show: true,
			targetDateTime: null,
			selectedServer: null,
			selectedVolume: null,
			expectedVolumeSize: null,
			currentVolumeSize: null,
		};
	},
	computed: {
		serverTypeOptions() {
			const options = [];
			if (this.servers.app) {
				options.push({
					label: this.servers.app,
					value: this.servers.app,
				});
			}

			if (this.servers.db) {
				options.push({
					label: this.servers.db,
					value: this.servers.db,
				});
			}

			if (this.servers.replica) {
				options.push({
					label: this.servers.replica,
					value: this.servers.replica,
				});
			}

			return options;
		},
		currentVolumes() {
			if (!this.selectedServer) return [];

			if (this.selectedServer === this.servers.db) {
				return this.$resources.dbServer?.doc?.data_volumes || [];
			} else if (this.selectedServer === this.servers.app) {
				return this.$resources.appServer?.doc?.data_volumes || [];
			} else if (this.selectedServer === this.servers.replica) {
				return this.$resources.replicaServer?.doc?.data_volumes || [];
			}

			return [];
		},
		isLoadingVolumes() {
			if (!this.selectedServer) return false;

			if (this.selectedServer === this.servers.db) {
				return this.$resources.dbServer?.loading;
			} else if (this.selectedServer === this.servers.app) {
				return this.$resources.appServer?.loading;
			} else if (this.selectedServer === this.servers.replica) {
				return this.$resources.replicaServer?.loading;
			}

			return false;
		},
		volumeOptions() {
			return this.currentVolumes.map((volume) => ({
				label: `${volume.volume_id} (${volume.size} GB)`,
				value: volume.volume_id,
			}));
		},
		datetimeInIST() {
			if (!this.targetDateTime) return null;
			return this.$dayjs(this.targetDateTime)
				.tz('Asia/Kolkata')
				.format('YYYY-MM-DDTHH:mm');
		},
		serverDoctype() {
			if (!this.selectedServer) return null;
			return this.selectedServer === this.servers.app
				? 'Server'
				: 'Database Server';
		},
		isResizeDisabled() {
			return (
				!this.selectedServer ||
				!this.selectedVolume ||
				!this.expectedVolumeSize ||
				this.expectedVolumeSize >= this.currentVolumeSize ||
				this.currentVolumes.length === 0 ||
				!this.targetDateTime
			);
		},
	},
	watch: {
		selectedServer() {
			// Reset when server changes
			this.selectedVolume = null;
			this.expectedVolumeSize = null;
			this.currentVolumeSize = null;
		},
		selectedVolume(newVolume) {
			if (newVolume) {
				const volume = this.currentVolumes.find(
					(v) => v.volume_id === newVolume,
				);
				if (volume) {
					this.currentVolumeSize = volume.size;
					this.expectedVolumeSize = null;
				}
			}
		},
	},
	resources: {
		dbServer() {
			if (!this.servers.db) return null;

			return {
				type: 'document',
				doctype: 'Database Server',
				name: this.servers.db,
				auto: true,
			};
		},
		appServer() {
			if (!this.servers.app) return null;

			return {
				type: 'document',
				doctype: 'Server',
				name: this.servers.app,
				auto: true,
			};
		},
		replicaServer() {
			if (!this.servers.replica) return null;

			return {
				type: 'document',
				doctype: 'Database Server',
				name: this.servers.replica,
				auto: true,
			};
		},
		virtualDiskResize() {
			return {
				url: 'press.api.server.schedule_disk_resize',
				params: {
					name: this.selectedServer,
					server_type: this.serverDoctype,
					volume_id: this.selectedVolume,
					expected_volume_size: this.expectedVolumeSize,
					scheduled_datetime: this.datetimeInIST,
				},
				onSuccess() {
					toast.success('Virtual disk resize has been scheduled.', {
						description: `Disk will be resized to ${this.expectedVolumeSize} GB for ${this.selectedServer}.`,
					});
					this.onDiskResizeCreation();
					this.show = false;
				},
				onError(error) {
					toast.error('Failed to schedule virtual disk resize.');
				},
			};
		},
	},
	methods: {
		resetValues() {
			this.targetDateTime = null;
			this.selectedServer = null;
			this.selectedVolume = null;
			this.expectedVolumeSize = null;
			this.currentVolumeSize = null;
		},
		resizeDisk() {
			if (!this.isResizeDisabled && this.$resources.virtualDiskResize) {
				this.$resources.virtualDiskResize.submit();
			}
		},
	},
};
</script>
