<template>
	<Dialog
		v-model="show"
		@close="resetValues"
		:options="{ title: 'Resize Virtual Disk' }"
	>
		<template #body-content>
			<div class="space-y-4">
				<p class="text-base">
					Shrink the virtual disk for <b>{{ server }}</b>
				</p>

				<div
					v-if="!volumes || volumes.length === 0"
					class="flex items-center rounded bg-red-50 p-4 text-sm text-red-700"
				>
					<lucide-alert-circle class="mr-2 h-4 w-4" />
					No volumes found for this server.
				</div>

				<template v-else>
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
import { getCachedDocumentResource } from 'frappe-ui';
import { toast } from 'vue-sonner';
import DateTimeControl from '../DateTimeControl.vue';

export default {
	name: 'VirtualDiskResizeDialog',
	props: ['server'],
	components: { DateTimeControl },
	data() {
		return {
			show: true,
			targetDateTime: null,
			selectedVolume: null,
			expectedVolumeSize: null,
			currentVolumeSize: null,
			volumes: [],
		};
	},
	computed: {
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
			return getCachedDocumentResource('Server', this.server);
		},
	},
	mounted() {
		// Fetch volumes and rate limit status from server doc if available
		if (this.$server.doc?.data_volumes) {
			this.volumes = this.$server.doc.volumes;
		}
	},
	watch: {
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
					name: this.server,
					server_type: this.$server.doc?.doctype,
					volume_id: this.selectedVolume,
					expected_volume_size: this.expectedVolumeSize,
					scheduled_datetime: this.datetimeInIST,
				},
				onSuccess() {
					toast.success('Virtual disk resize has been scheduled.', {
						description: `Disk will be resized to ${this.expectedVolumeSize} GB.`,
					});
					this.show = false;
				},
			};
		},
	},
	methods: {
		resetValues() {
			this.targetDateTime = null;
			this.selectedVolume = null;
			this.expectedVolumeSize = null;
			this.currentVolumeSize = null;
		},
	},
};
</script>
