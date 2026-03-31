<template>
	<div
		:class="`flex items-center justify-between rounded-md border border-${color}-200 bg-${color}-100 px-3.5 py-2.5`"
	>
		<div class="flex items-center">
			<lucide-alert-triangle
				v-if="showIcon && (type === 'error' || type === 'warning')"
				:class="`h-4 w-8 text-${color}-600`"
			/>
			<lucide-info
				v-if="showIcon && type === 'info'"
				:class="`h-4 w-8 text-${color}-600`"
			/>
			<div
				:class="{ 'ml-3': showIcon }"
				class="text-p-base font-medium text-gray-800"
				v-html="title"
			/>
		</div>

		<div class="flex items-center">
			<!-- Button Slot -->
			<slot></slot>

			<div
				class="flex items-center justify-center overflow-hidden rounded-sm"
				v-if="isDismissible"
			>
				<Button
					class="ml-1 transition-colors focus:outline-none text-ink-gray-8 bg-gray-700 bg-opacity-0 hover:bg-opacity-[4%] active:bg-opacity-[8%] h-7 w-7 rounded"
					variant="ghost"
					theme="colors"
					@click="$emit('dismissBanner')"
				>
					<template #icon>
						<lucide-x class="h-4 w-4" />
					</template>
				</Button>
			</div>
		</div>
	</div>
</template>
<script>
const colors = {
	info: 'blue',
	success: 'green',
	error: 'red',
	warning: 'amber',
	general: 'gray',
};

export default {
	name: 'AlertBanner',
	props: {
		title: String,
		type: {
			type: String,
			default: 'info',
		},
		showIcon: {
			type: Boolean,
			default: true,
		},
		isDismissible: {
			type: Number,
			default: 0,
		},
	},
	computed: {
		color() {
			return colors[this.type] ?? 'gray';
		},
	},
};
</script>
