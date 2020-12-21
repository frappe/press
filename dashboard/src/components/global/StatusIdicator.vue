<template>
	<span
		class="inline-block px-1 py-1 text-xs font-medium rounded-full cursor-default"
		:class="classes"
	>
	</span>
</template>
<script>
export default {
	name: 'StatusIdicator',
	props: ['color', 'usage'],
	computed: {
		classes() {
			let color = this.color;
			let usage = this.usage;

			if (!color && usage) {
				if (usage > 90) {
					color = 'red';
				} else if (usage > 80) {
					color = 'orange';
				} else if (usage > 70) {
					color = 'yellow';
				} else {
					color = 'green';
				}
			}

			return {
				green: 'bg-green-400',
				yellow: 'bg-yellow-400',
				orange: 'bg-orange-400',
				red: 'bg-red-500'
			}[color || 'green'];
		}
	}
};
</script>
