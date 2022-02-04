<template>
	<svg
		viewBox="0 0 48 24"
		preserveAspectRatio="xMidYMin slice"
		class="h-12 w-12"
	>
		<circle cx="24" cy="24" r="9" fill="#fff"></circle>
		<circle
			class="stroke-current text-gray-200"
			cx="24"
			cy="24"
			r="9"
			fill="transparent"
			stroke-width="4"
		></circle>
		<circle
			class="stroke-current"
			:class="colorClass"
			cx="24"
			cy="24"
			r="9"
			fill="transparent"
			stroke-width="4"
			:stroke-dasharray="circumference"
			:stroke-dashoffset="dashOffset"
		></circle>
	</svg>
</template>
<script>
export default {
	name: 'ProgressArc',
	props: ['percentage'],
	computed: {
		circumference() {
			return 2 * Math.PI * 9;
		},
		dashOffset() {
			let halfCircumference = this.circumference / 2;
			if (isNaN(this.percentage)) {
				return halfCircumference;
			}
			let percentage = this.percentage;
			if (percentage > 100) {
				percentage = 100;
			}
			return halfCircumference - (percentage / 100) * halfCircumference;
		},
		colorClass() {
			if (this.percentage < 60) {
				return 'text-green-500';
			}
			if (this.percentage < 80) {
				return 'text-yellow-500';
			}
			if (this.percentage >= 80) {
				return 'text-red-500';
			}
		}
	}
};
</script>
