<template>
	<Dialog v-model="show" :options="{ title: 'Disk Resize Details' }">
		<template #body-content>
			<div
				v-if="this.$resources.virtualdiskresize.loading"
				class="flex items-center justify-center py-12"
			>
				<div class="text-center">
					<div
						class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mb-2"
					></div>
					<p class="text-sm text-gray-500">Loading resize details...</p>
				</div>
			</div>
			<div v-else class="space-y-6">
				<!-- Overview Section -->
				<div>
					<div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
						<div class="flex items-start gap-3">
							<div class="flex-shrink-0 mt-0.5">
								<svg
									class="w-5 h-5 text-blue-600"
									fill="none"
									stroke="currentColor"
									viewBox="0 0 24 24"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01"
									/>
								</svg>
							</div>
							<div class="flex-1 min-w-0">
								<div class="flex items-center gap-3 mb-1">
									<h4 class="text-sm font-semibold text-gray-900">
										{{ resizeData.virtual_machine }}
									</h4>
									<span
										:class="statusClass"
										class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
									>
										{{ resizeData.status }}
									</span>
								</div>
								<p class="text-sm text-gray-600">
									<span v-if="resizeData.scheduled_time">
										Scheduled: {{ formatDateTime(resizeData.scheduled_time) }}
									</span>
								</p>
							</div>
						</div>
					</div>
				</div>

				<!-- Volume Details Grid -->
				<div class="grid grid-cols-2 gap-4">
					<!-- Old Volume -->
					<div class="bg-gray-50 rounded-lg p-4 border border-gray-200">
						<h3
							class="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2"
						>
							<svg
								class="w-4 h-4"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M4 7v10c0 2 1 3 3 3h10c2 0 3-1 3-3V7c0-2-1-3-3-3H7C5 4 4 5 4 7z"
								/>
							</svg>
							Old Volume
						</h3>
						<div class="space-y-3">
							<div>
								<div class="text-xs text-gray-500 mb-0.5">Volume ID</div>
								<div class="text-sm font-mono text-gray-900 truncate">
									{{ resizeData.old_volume_id || 'N/A' }}
								</div>
							</div>
							<div>
								<div class="text-xs text-gray-500 mb-0.5">Status</div>
								<div class="text-sm font-medium text-gray-900">
									{{ resizeData.old_volume_status || 'N/A' }}
								</div>
							</div>
							<div>
								<div class="text-xs text-gray-500 mb-0.5">Size</div>
								<div class="text-sm font-medium text-gray-900">
									{{ resizeData.old_volume_size }} GB
								</div>
							</div>
						</div>
					</div>

					<!-- New Volume -->
					<div class="bg-green-50 rounded-lg p-4 border border-green-200">
						<h3
							class="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2"
						>
							<svg
								class="w-4 h-4 text-green-600"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M4 7v10c0 2 1 3 3 3h10c2 0 3-1 3-3V7c0-2-1-3-3-3H7C5 4 4 5 4 7z"
								/>
							</svg>
							New Volume
						</h3>
						<div class="space-y-3">
							<div>
								<div class="text-xs text-gray-500 mb-0.5">Volume ID</div>
								<div class="text-sm font-mono text-gray-900 truncate">
									{{ resizeData.new_volume_id || 'N/A' }}
								</div>
							</div>
							<div>
								<div class="text-xs text-gray-500 mb-0.5">Status</div>
								<div class="text-sm font-medium text-gray-900">
									{{ resizeData.new_volume_status }}
								</div>
							</div>
							<div>
								<div class="text-xs text-gray-500 mb-0.5">Size</div>
								<div class="text-sm font-medium text-green-700">
									{{
										resizeData.new_volume_size || resizeData.expected_disk_size
									}}
									GB
								</div>
							</div>
						</div>
					</div>
				</div>

				<!-- Downtime Information -->
				<div
					v-if="hasDowntimeInfo"
					class="bg-amber-50 border border-amber-200 rounded-lg p-4"
				>
					<h3
						class="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2"
					>
						<svg
							class="w-4 h-4 text-amber-600"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
							/>
						</svg>
						Downtime Info
					</h3>
					<div class="grid grid-cols-3 gap-4">
						<div>
							<div class="text-xs text-gray-500 mb-0.5">Start Time</div>
							<div class="text-sm font-medium text-gray-900">
								{{
									resizeData.downtime_start
										? formatDateTime(resizeData.downtime_start)
										: 'N/A'
								}}
							</div>
						</div>
						<div>
							<div class="text-xs text-gray-500 mb-0.5">End Time</div>
							<div class="text-sm font-medium text-gray-900">
								{{
									resizeData.downtime_end
										? formatDateTime(resizeData.downtime_end)
										: 'N/A'
								}}
							</div>
						</div>
						<div>
							<div class="text-xs text-gray-500 mb-0.5">Duration</div>
							<div class="text-sm font-medium text-amber-700">
								{{ resizeData.downtime_duration || 'N/A' }}
							</div>
						</div>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>
<script>
export default {
	name: 'ServerDiskResizeDetailsDialog',
	props: {
		resizeName: {
			type: String,
			required: true,
		},
	},
	data() {
		return {
			show: true,
		};
	},
	computed: {
		resizeData() {
			const doc = this.$resources.virtualdiskresize?.doc || {};
			return {
				virtual_machine: doc.virtual_machine,
				status: doc.status,
				downtime_start: doc.downtime_start,
				downtime_end: doc.downtime_end,
				downtime_duration: doc.downtime_duration,
				old_volume_id: doc.old_volume_id,
				old_volume_status: doc.old_volume_status,
				old_volume_size: doc.old_volume_size,
				new_volume_id: doc.new_volume_id,
				new_volume_status: doc.new_volume_status,
				new_volume_size: doc.new_volume_size,
				scheduled_time: doc.scheduled_time,
				expected_disk_size: doc.expected_disk_size,
			};
		},
		statusClass() {
			const status = this.resizeData.status?.toLowerCase();
			const statusMap = {
				completed: 'bg-green-100 text-green-800',
				'in progress': 'bg-blue-100 text-blue-800',
				pending: 'bg-yellow-100 text-yellow-800',
				failed: 'bg-red-100 text-red-800',
				cancelled: 'bg-gray-100 text-gray-800',
			};
			return statusMap[status] || 'bg-gray-100 text-gray-800';
		},
		hasDowntimeInfo() {
			return (
				this.resizeData.downtime_start ||
				this.resizeData.downtime_end ||
				this.resizeData.downtime_duration
			);
		},
	},
	resources: {
		virtualdiskresize() {
			console.log('Fetching virtual disk resize details for:', this.resizeName);
			if (!this.resizeName) return;

			return {
				type: 'document',
				doctype: 'Virtual Disk Resize',
				name: this.resizeName,
				auto: true,
			};
		},
	},
	methods: {
		formatDateTime(datetime) {
			if (!datetime) return 'N/A';
			return this.$dayjs(datetime).format('MMM DD, YYYY hh:mm A');
		},
	},
};
</script>
