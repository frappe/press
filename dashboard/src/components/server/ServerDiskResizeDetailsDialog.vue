<template>
	<Dialog v-model="show" :options="{ title: 'Disk Resize Details' }">
		<template #body-content>
			<div class="space-y-6">
				<!-- Downtime Information -->
				<div v-if="hasDowntimeInfo" class="space-y-3">
					<h3 class="text-sm font-semibold text-gray-900">
						Downtime Information
					</h3>
					<div class="space-y-2">
						<div class="flex justify-between text-sm">
							<span class="text-gray-600">Start Time:</span>
							<span class="font-medium text-gray-900">{{
								formatDateTime(resizeDetails.downtime_start)
							}}</span>
						</div>
						<div class="flex justify-between text-sm">
							<span class="text-gray-600">End Time:</span>
							<span class="font-medium text-gray-900">{{
								formatDateTime(resizeDetails.downtime_end)
							}}</span>
						</div>
						<div class="flex justify-between text-sm">
							<span class="text-gray-600">Duration:</span>
							<span class="font-medium text-gray-900">{{
								resizeDetails.downtime_duration
							}}</span>
						</div>
					</div>
				</div>

				<div v-if="hasDowntimeInfo" class="border-t border-gray-200"></div>

				<!-- Old Volume Details -->
				<div class="space-y-3">
					<h3 class="text-sm font-semibold text-gray-900">Previous Volume</h3>
					<div class="space-y-2">
						<div class="flex justify-between text-sm">
							<span class="text-gray-600">Volume ID:</span>
							<span class="font-mono text-xs font-medium text-gray-900">{{
								resizeDetails.old_volume_id
							}}</span>
						</div>
						<div class="flex justify-between text-sm">
							<span class="text-gray-600">Status:</span>
							<span
								class="font-medium"
								:class="getStatusClass(resizeDetails.old_volume_status)"
							>
								{{ resizeDetails.old_volume_status }}
							</span>
						</div>
						<div class="flex justify-between text-sm">
							<span class="text-gray-600">Size:</span>
							<span class="font-medium text-gray-900"
								>{{ resizeDetails.old_volume_size }} GB</span
							>
						</div>
						<div class="flex justify-between text-sm">
							<span class="text-gray-600">IOPS:</span>
							<span class="font-medium text-gray-900">{{
								resizeDetails.old_volume_iops
							}}</span>
						</div>
						<div class="flex justify-between text-sm">
							<span class="text-gray-600">Throughput:</span>
							<span class="font-medium text-gray-900"
								>{{ resizeDetails.old_volume_throughput }} MB/s</span
							>
						</div>
					</div>
				</div>

				<div class="border-t border-gray-200"></div>

				<!-- New Volume Details -->
				<div v-if="hasNewVolumeInfo" class="space-y-3">
					<h3 class="text-sm font-semibold text-gray-900">New Volume</h3>
					<div class="space-y-2">
						<div class="flex justify-between text-sm">
							<span class="text-gray-600">Volume ID:</span>
							<span class="font-mono text-xs font-medium text-gray-900">{{
								resizeDetails.new_volume_id
							}}</span>
						</div>
						<div class="flex justify-between text-sm">
							<span class="text-gray-600">Status:</span>
							<span
								class="font-medium"
								:class="getStatusClass(resizeDetails.new_volume_status)"
							>
								{{ resizeDetails.new_volume_status }}
							</span>
						</div>
						<div class="flex justify-between text-sm">
							<span class="text-gray-600">Size:</span>
							<span class="font-medium text-gray-900"
								>{{ resizeDetails.new_volume_size }} GB</span
							>
						</div>
						<div class="flex justify-between text-sm">
							<span class="text-gray-600">IOPS:</span>
							<span class="font-medium text-gray-900">{{
								resizeDetails.new_volume_iops
							}}</span>
						</div>
						<div class="flex justify-between text-sm">
							<span class="text-gray-600">Throughput:</span>
							<span class="font-medium text-gray-900"
								>{{ resizeDetails.new_volume_throughput }} MB/s</span
							>
						</div>
					</div>
				</div>

				<div
					v-else
					class="flex items-center rounded bg-blue-50 p-4 text-sm text-blue-700"
				>
					<lucide-info class="mr-2 h-4 w-4" />
					New volume details will be available after the resize operation
					completes.
				</div>
			</div>
		</template>
		<template #actions>
			<Button
				class="w-full"
				variant="solid"
				label="Close"
				@click="show = false"
			/>
		</template>
	</Dialog>
</template>

<script>
export default {
	name: 'ServerDiskResizeDetailsDialog',
	props: {
		resizeDetails: {
			type: Object,
			required: true,
			default: () => ({
				downtime_start: null,
				downtime_end: null,
				downtime_duration: null,
				old_volume_id: null,
				old_volume_status: null,
				old_volume_size: null,
				old_volume_iops: null,
				old_volume_throughput: null,
				new_volume_id: null,
				new_volume_status: null,
				new_volume_size: null,
				new_volume_iops: null,
				new_volume_throughput: null,
			}),
		},
	},
	data() {
		return {
			show: true,
		};
	},
	computed: {
		hasDowntimeInfo() {
			return (
				this.resizeDetails.downtime_start ||
				this.resizeDetails.downtime_end ||
				this.resizeDetails.downtime_duration
			);
		},
		hasNewVolumeInfo() {
			return (
				this.resizeDetails.new_volume_id ||
				this.resizeDetails.new_volume_status ||
				this.resizeDetails.new_volume_size
			);
		},
	},
	methods: {
		formatDateTime(datetime) {
			if (!datetime) return 'N/A';
			return this.$dayjs(datetime).format('MMM DD, YYYY hh:mm A');
		},
		getStatusClass(status) {
			if (!status) return 'text-gray-900';

			const statusLower = status.toLowerCase();
			if (statusLower === 'available' || statusLower === 'in-use') {
				return 'text-green-700';
			} else if (statusLower === 'creating' || statusLower === 'modifying') {
				return 'text-blue-700';
			} else if (statusLower === 'error' || statusLower === 'deleted') {
				return 'text-red-700';
			}
			return 'text-gray-900';
		},
	},
};
</script>
