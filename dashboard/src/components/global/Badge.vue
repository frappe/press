<template>
	<span
		class="inline-block px-3 py-1 text-xs font-medium rounded-md cursor-default"
		:class="classes"
	>
		<slot>{{ badgeText }}</slot>
	</span>
</template>
<script>
export default {
	name: 'Badge',
	props: ['color', 'status', 'usage', 'badgeText'],
	computed: {
		classes() {
			let color = this.color;
			let usage = this.usage;
			this.badgeText = this.status;

			if (usage && usage > 70) {
				// this is specific to site usage
				if (usage > 95) {
					color = 'red';
				} else if (usage > 80) {
					color = 'orange';
				} else {
					color = 'yellow';
				}
				if (this.status == 'Active') {
					this.badgeText = 'Attention Required';
				}
			}
			if (!color && this.status) {
				color = {
					Pending: 'orange',
					Running: 'yellow',
					Success: 'green',
					Failure: 'red',
					Active: 'green',
					Broken: 'red',
					Updating: 'blue',
					Installing: 'orange',
					Rejected: 'red',
					'Update Available': 'blue',
					'Awaiting Approval': 'orange'
				}[this.status];
			}
			return {
				gray: 'text-gray-700 bg-gray-50',
				green: 'text-green-700 bg-green-50',
				red: 'text-red-700 bg-red-50',
				yellow: 'text-yellow-700 bg-yellow-50',
				blue: 'text-blue-700 bg-blue-50',
				orange: 'text-orange-700 bg-orange-50'
			}[color || 'gray'];
		}
	}
};
</script>
