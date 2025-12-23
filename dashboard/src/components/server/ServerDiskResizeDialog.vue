<template>
	<Dialog
		v-model="show"
		@close="resetValues"
		:options="{ title: 'Manage Storage' }"
	>
		<template #body-content>
			<div class="space-y-4">
				<FormControl
					label="Action"
					type="select"
					v-model="selectedAction"
					:options="actionOptions"
					placeholder="Choose an action"
				/>

				<!-- Increase Storage Section -->
				<template v-if="selectedAction === 'increase'">
					<div
						class="rounded mt-4 p-2 text-sm text-gray-700 bg-gray-100 border"
					>
						You will be charged at the rate of
						<strong> {{ perGBRatePerMonth }}/mo </strong>
						for each additional GB of storage.

						<template v-if="additionalStorageIncrementRecommendation">
							<br />
							<br />Recommended storage increment:
							<strong
								>{{ additionalStorageIncrementRecommendation }} GiB</strong
							>
						</template>
					</div>

					<p class="mt-4 text-sm text-gray-700">
						<strong>Note</strong>: You can increase the storage size of the
						server only once in 6 hours.
					</p>
					<FormControl
						label="Storage (GB)"
						type="select"
						v-model="storageIncrement"
						:options="storageIncrementOptions"
						placeholder="Choose increment size"
					/>
				</template>

				<!-- Reduce Storage Section -->
				<template v-if="selectedAction === 'reduce'">
					<div
						v-if="currentVolumes.length === 0 && !isLoadingVolumes"
						class="flex items-center rounded bg-red-50 p-4 text-sm text-red-700"
					>
						<lucide-alert-circle class="mr-2 h-4 w-4" />
						No volumes to shrink found for this server.
					</div>

					<template v-if="currentVolumes.length > 0">
						<div
							class="flex items-center rounded bg-yellow-50 p-4 text-sm text-yellow-700"
						>
							<lucide-alert-triangle class="mr-2 h-4 w-4" />
							<span
								><b>Warning:</b> Reducing storage will cause server downtime
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
							v-model="newVolumeSize"
							:max="currentVolumeSize - 5"
							:step="5"
							placeholder="Enter size in GB"
						/>

						<div
							v-if="newVolumeSize && newVolumeSize >= currentVolumeSize"
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
				</template>
			</div>
		</template>
		<template #actions>
			<Button
				v-if="selectedAction"
				class="w-full"
				variant="solid"
				:label="actionButtonLabel"
				:disabled="isActionDisabled"
				:loading="$resources.storageOperation?.loading"
				@click="performStorageAction"
			/>
		</template>
	</Dialog>
</template>

<script>
import { toast } from 'vue-sonner';
import DateTimeControl from '../DateTimeControl.vue';

export default {
	name: 'ManageStorageDialog',
	props: {
		server: {
			type: Object,
			required: true,
		},
		perGBRatePerMonth: {
			type: Number,
			required: true,
		},
		additionalStorageIncrementRecommendation: {
			type: Number,
			default: null,
		},
		onStorageOperationComplete: {
			type: Function,
			default: () => {},
		},
	},
	components: { DateTimeControl },
	data() {
		return {
			show: true,
			selectedAction: null,
			targetDateTime: null,
			selectedVolume: null,
			newVolumeSize: null,
			currentVolumeSize: null,
			storageIncrement: null,
		};
	},
	computed: {
		actionOptions() {
			return [
				{ label: 'Increase Storage', value: 'increase' },
				{ label: 'Reduce Storage', value: 'reduce' },
			];
		},
		storageIncrementOptions() {
			return Array.from({ length: 100 }, (_, i) => ({
				label: `${(i + 1) * 5} GB`,
				value: (i + 1) * 5,
			}));
		},
		currentVolumes() {
			if (!this.server) return [];
			return this.$resources.$server?.doc?.data_volumes || [];
		},
		isLoadingVolumes() {
			if (!this.server) return false;
			return this.$resources.$server?.loading;
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
		actionButtonLabel() {
			if (this.selectedAction === 'increase') {
				return 'Increase Storage';
			} else if (this.selectedAction === 'reduce') {
				return 'Reduce Storage';
			}
		},
		isActionDisabled() {
			if (!this.selectedAction) {
				return true;
			}

			if (this.selectedAction === 'increase') {
				return !this.storageIncrement;
			}

			if (this.selectedAction === 'reduce') {
				if (
					!this.selectedVolume ||
					!this.newVolumeSize ||
					!this.targetDateTime
				) {
					return true;
				}
				return this.newVolumeSize >= this.currentVolumeSize;
			}

			return false;
		},
	},
	watch: {
		selectedAction() {
			// Reset fields when action changes
			this.selectedVolume = null;
			this.newVolumeSize = null;
			this.currentVolumeSize = null;
			this.targetDateTime = null;
			this.storageIncrement = null;
		},
		selectedVolume(newVolume) {
			if (newVolume) {
				const volume = this.currentVolumes.find(
					(v) => v.volume_id === newVolume,
				);
				if (volume) {
					this.currentVolumeSize = volume.size;
					this.newVolumeSize = null;
				}
			}
		},
	},
	resources: {
		$server() {
			if (!this.server?.name) return null;

			return {
				type: 'document',
				doctype: this.server.doctype,
				name: this.server.name,
				auto: true,
				whitelistedMethods: {
					increaseDiskSize: 'increase_disk_size_for_server',
					reduceDiskSize: 'schedule_disk_resize',
				},
			};
		},
		storageOperation() {
			if (this.selectedAction === 'increase') {
				return {
					method: 'increaseDiskSize',
					params: {
						increment: Number(this.storageIncrement),
					},
					onSuccess: () => {
						toast.success('Disk size is scheduled to increase');
						this.onStorageOperationComplete();
						this.show = false;
					},
					onError: (e) => {
						console.error(e);
						toast.error('Failed to increase disk size');
					},
				};
			}

			return {
				method: 'reduceDiskSize',
				params: {
					volume_id: this.selectedVolume,
					expected_volume_size: this.newVolumeSize,
					scheduled_datetime: this.datetimeInIST,
				},
				onSuccess: () => {
					toast.success('Storage reduction has been scheduled.', {
						description: `Disk will be resized to ${this.newVolumeSize} GB.`,
					});
					this.onStorageOperationComplete();
					this.show = false;
				},
				onError: (error) => {
					console.error(error);
					toast.error('Failed to schedule disk size reduction');
				},
			};
		},
	},
	methods: {
		resetValues() {
			this.selectedAction = null;
			this.targetDateTime = null;
			this.selectedVolume = null;
			this.newVolumeSize = null;
			this.currentVolumeSize = null;
			this.storageIncrement = null;
		},
		performStorageAction() {
			if (!this.isActionDisabled && this.$resources.storageOperation) {
				this.$resources.storageOperation.submit();
			}
		},
	},
};
</script>
