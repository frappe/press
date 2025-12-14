<template>
	<Dialog
		v-model="show"
		@close="resetValues"
		:options="{ title: 'Resize Virtual Disk' }"
	>
		<template #body-content>
			<div class="space-y-4">
				<p class="text-base">Select a server and shrink its disk size</p>

				<FormControl
					label="Select Server"
					type="select"
					v-model="selectedServer"
					:options="serverTypeOptions"
					placeholder="Choose a server"
				/>

				<div
					v-if="selectedServer && (!volumes || volumes.length === 0)"
					class="flex items-center rounded bg-red-50 p-4 text-sm text-red-700"
				>
					<lucide-alert-circle class="mr-2 h-4 w-4" />
					No volumes found for this server.
				</div>

				<template v-if="selectedServer && volumes && volumes.length > 0">
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
						label="Schedule Time in IST"
					/>
				</template>
			</div>
		</template>
		<template #actions>
			<Button
				class="w-full"
				variant="solid"
				label="Resize Disk"
				:disabled="
					!selectedServer ||
					!selectedVolume ||
					!expectedVolumeSize ||
					expectedVolumeSize >= currentVolumeSize ||
					!volumes ||
					volumes.length === 0
				"
				:loading="$resources.virtualDiskResize.loading"
				@click="$resources.virtualDiskResize.submit()"
			/>
		</template>
	</Dialog>
</template>

<script>
import { toast } from 'vue-sonner';
import DateTimeControl from '../DateTimeControl.vue';
import { getDocResource } from '../../utils/resource';

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
			volumes: [],
		};
	},
	computed: {
		serverTypeOptions() {
			const options = [];

			options.push([
				{
					label: this.servers.app,
					value: this.servers.app,
				},
				{
					label: this.servers.db,
					value: this.servers.db,
				},
			]);

			if (this.servers.secondary_app) {
				options.push({
					label: this.servers.secondary_app,
					value: this.servers.secondary_app,
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
		volumeOptions() {
			return this.volumes.map((volume) => ({
				label: `${volume.name} (${volume.size} GB)`,
				value: volume.name,
			}));
		},
		datetimeInIST() {
			if (!this.targetDateTime) return null;
			const datetimeInIST = this.$dayjs(this.targetDateTime).format(
				'YYYY-MM-DDTHH:mm',
			);
			return datetimeInIST;
		},
		$server() {
			if (!this.selectedServer) return null;

			let doctype = 'Server';
			if (
				![this.servers.app, this.servers.secondary_app].includes(
					this.selectedServer,
				)
			) {
				doctype = 'Database Server';
			}

			return getDocResource(doctype, this.selectedServer);
		},
	},
	watch: {
		selectedServer(newType) {
			// Reset when server type changes
			this.selectedVolume = null;
			this.expectedVolumeSize = null;
			this.currentVolumeSize = null;
			this.volumes = [];

			// Load volumes for new server
			if (newType && this.$server?.doc?.data_volumes) {
				this.volumes = this.$server.doc.data_volumes;
			}
		},
		selectedVolume(newVolume) {
			if (newVolume) {
				const volume = this.volumes.find((v) => v.name === newVolume);
				if (volume) {
					this.currentVolumeSize = volume.size;
					this.expectedVolumeSize = null; // Reset when changing volume
				}
			}
		},
	},
	resources: {
		virtualDiskResize() {
			return {
				url: 'press.api.server.schedule_disk_resize',
				params: {
					name: this.selectedServer,
					server_type: this.$server?.doc?.doctype,
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
			this.volumes = [];
		},
	},
};
</script>
