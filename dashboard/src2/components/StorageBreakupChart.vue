<template>
	<div>
		<!-- Slider -->
		<div
			v-if="showSlider"
			class="mb-4 mt-4 flex h-7 w-full items-start justify-start overflow-clip rounded border bg-gray-50 pl-0"
			:class="{
				'cursor-pointer': onclickSlider,
			}"
			@click="onclickSlider ? onclickSlider() : null"
		>
			<div
				v-for="(key, idx) in dataKeys"
				:key="key"
				class="h-7"
				:style="{
					backgroundColor: colorPalette[idx],
					width: `${getPercentage(key)}%`,
				}"
			></div>
		</div>
		<!-- Table -->
		<div
			class="full flex w-full flex-col items-start justify-start overflow-y-auto rounded px-1.5"
		>
			<div
				v-for="(key, idx) in dataKeys"
				:key="key"
				class="flex w-full items-center justify-start gap-x-2 py-3"
				:class="{ 'border-t': idx !== 0 }"
			>
				<div
					v-if="colorPalette.length > idx"
					class="h-2 w-2 rounded-full"
					:style="{ backgroundColor: colorPalette[idx] }"
				></div>
				<span class="text-sm text-gray-800">
					<component
						v-if="keyFormatter && typeof keyFormatter(key) === 'object'"
						:is="keyFormatter(key)"
					/>
					<template v-else>
						{{ keyFormatter ? keyFormatter(key) : key }}
					</template></span
				>
				<span class="ml-auto text-sm text-gray-800">
					{{ valueFormatter ? valueFormatter(key, data[key]) : data[key] }}
				</span>
			</div>
		</div>
	</div>
</template>

<script>
export default {
	name: 'StorageBreakupChart',
	props: {
		colorPalette: {
			type: Array,
			default: [],
		},
		data: {
			type: Object,
			required: true,
		},
		keyFormatter: {
			type: Function,
			default: null,
		},
		valueFormatter: {
			type: Function,
			default: null,
		},
		stickyKeys: {
			type: Array,
			default: () => [],
		},
		hiddenKeysInSlider: {
			type: Array,
			default: () => [],
		},
		showSlider: {
			type: Boolean,
			default: true,
		},
		onclickSlider: {
			type: Function,
			default: null,
		},
		showTopN: {
			type: Number,
			default: 0, // Default to showing all keys
		},
	},
	computed: {
		dataKeys() {
			let keys = Object.keys(this.data);
			if (this.stickyKeys.length > 0) {
				const sticky = this.stickyKeys.filter((key) => key in this.data);
				const rest = Object.keys(this.data)
					.filter((key) => !this.stickyKeys.includes(key))
					.sort((a, b) => Number(this.data[b]) - Number(this.data[a]));
				return sticky.concat(rest).slice(0, this.showTopN || keys.length);
			}
			// Sort all keys if no stickyKeys
			return keys
				.sort((a, b) => Number(this.data[b]) - Number(this.data[a]))
				.splice(0, this.showTopN || keys.length);
		},
		total() {
			// Sum all values for percentage calculation
			return (
				Object.values(this.data).reduce((a, b) => Number(a) + Number(b), 0) || 1
			);
		},
	},
	methods: {
		getPercentage(key) {
			if (this.hiddenKeysInSlider.includes(key)) {
				return 0; // Return 0% for hidden keys in slider
			}
			return ((Number(this.data[key]) / this.total) * 100).toFixed(2);
		},
	},
};
</script>
