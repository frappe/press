<template>
	<div
		:class="`flex items-center justify-between rounded-md border border-${color}-200 bg-${color}-100 px-3.5 py-2.5`"
	>
		<i-lucide-alert-triangle :class="`h-4 w-4 text-${color}-600`" />
		<div
			class="ml-3 text-p-base font-medium text-gray-800"
			v-html="title"
		></div>

		<!-- Button Slot -->
		<slot></slot>
	</div>
</template>
<script>
const colors = {
	info: 'blue',
	success: 'green',
	error: 'red',
	warning: 'amber'
};

export default {
	name: 'AlertBanner',
	props: {
		title: String,
		type: {
			type: String,
			default: 'info'
		}
	},
	computed: {
		color() {
			return colors[this.type] ?? 'gray';
		}
	}
};
</script>
