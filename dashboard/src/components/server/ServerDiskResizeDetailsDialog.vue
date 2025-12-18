<template>
	<Dialog v-model="show" :options="{ title: 'Disk Resize Details' }">
		<template #body-content>
			<div class="space-y-6">
				<!-- OLD VOLUME -->
				<div v-if="groups.oldVolume.length">
					<h3
						class="text-base font-semibold text-gray-500 uppercase tracking-wide mb-3"
					>
						Old Volume
					</h3>
					<div class="bg-gray-50 rounded-lg p-4 space-y-2.5">
						<div
							v-for="item in groups.oldVolume"
							:key="item.key"
							class="flex items-baseline gap-4"
						>
							<span class="text-base text-gray-600 font-medium">{{
								item.label
							}}</span>
							<span class="text-base text-gray-900 ml-auto">
								{{ item.value }}
							</span>
						</div>
					</div>
				</div>

				<!-- NEW VOLUME -->
				<div v-if="groups.newVolume.length">
					<h3
						class="text-base font-semibold text-gray-500 uppercase tracking-wide mb-3"
					>
						New Volume
					</h3>
					<div class="bg-gray-50 rounded-lg p-4 space-y-2.5">
						<div
							v-for="item in groups.newVolume"
							:key="item.key"
							class="flex items-baseline gap-4"
						>
							<span class="text-base text-gray-600 font-medium">{{
								item.label
							}}</span>
							<span class="text-base text-gray-900 ml-auto">
								{{ item.value }}
							</span>
						</div>
					</div>
				</div>

				<!-- DOWNTIME -->
				<div v-if="groups.downtime.length">
					<h3
						class="text-base font-semibold text-gray-500 uppercase tracking-wide mb-3"
					>
						Downtime Information
					</h3>
					<div class="bg-gray-50 rounded-lg p-4 space-y-2.5">
						<div
							v-for="item in groups.downtime"
							:key="item.key"
							class="flex items-baseline gap-4"
						>
							<span class="text-base text-gray-600 font-medium">{{
								item.label
							}}</span>
							<span class="text-base text-gray-900 ml-auto">
								{{ item.value }}
							</span>
						</div>
					</div>
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
		},
	},
	data() {
		return {
			show: true,
		};
	},
	computed: {
		groups() {
			const map = {
				downtime: [],
				oldVolume: [],
				newVolume: [],
			};

			Object.entries(this.resizeDetails).forEach(([key, value]) => {
				// Skip null / undefined everywhere
				if (value === null || value === undefined) return;
				// Skip 0 values for new volume fields
				if (key.startsWith('new_volume_') && value === 0) return;

				const item = {
					key,
					label: this.formatLabel(key),
					value: this.formatValue(key, value),
				};

				if (key.startsWith('downtime_')) {
					map.downtime.push(item);
				} else if (key.startsWith('old_volume_')) {
					map.oldVolume.push(item);
				} else if (key.startsWith('new_volume_')) {
					map.newVolume.push(item);
				}
			});

			return map;
		},
	},
	methods: {
		formatLabel(key) {
			return key
				.replace(/^(downtime_|old_volume_|new_volume_)/, '')
				.replace(/_/g, ' ')
				.replace(/\b\w/g, (c) => c.toUpperCase());
		},
		formatValue(key, value) {
			if (key.includes('downtime') && !key.includes('duration')) {
				return this.formatDateTime(value);
			}
			if (key.includes('size')) {
				return `${value} GB`;
			}
			return value;
		},
		formatDateTime(datetime) {
			if (!datetime) return 'N/A';
			return this.$dayjs(datetime).format('MMM DD, YYYY hh:mm A');
		},
	},
};
</script>
