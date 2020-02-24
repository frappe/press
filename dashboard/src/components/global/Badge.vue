<template>
	<span class="px-3 py-1 rounded text-xs inline-block" :class="classes">
		<slot></slot>
	</span>
</template>
<script>
export default {
	name: 'Badge',
	props: ['color', 'status'],
	computed: {
		classes() {
			let color = this.color;
			if (!color && this.status) {
				color = {
					Pending: 'orange',
					Running: 'yellow',
					Success: 'green',
                    Failure: 'red',
                    Active: 'green',
                    Installing: 'orange'
				}[this.status];
			}
			return {
				gray: 'text-gray-700 bg-gray-200',
				green: 'text-green-700 bg-green-200',
				red: 'text-red-700 bg-red-200',
				yellow: 'text-yellow-700 bg-yellow-200',
				orange: 'text-orange-700 bg-orange-200'
			}[color || 'gray'];
		}
	}
};
</script>
