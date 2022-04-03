<template>
	<div ref="target"></div>
</template>
<script>
import { Chart } from 'frappe-charts/dist/frappe-charts.esm.js';
export default {
	name: 'FrappeChart',
	props: ['type', 'data', 'options', 'colors'],
	unmounted() {
		this.chart?.destroy();
	},
	watch: {
		data: {
			handler(value) {
				if (this.chart) {
					this.chart.update(value);
				} else {
					this.makeChart();
				}
			},
			immediate: true
		}
	},
	methods: {
		makeChart() {
			if (!this.data) return;

			this.$nextTick(() => {
				this.chart = new Chart(this.$refs['target'], {
					data: this.data,
					type: this.type,
					colors: this.colors,
					...this.options
				});

				this.updateGradient();
				this.removeOverflowFromContainer();
			});
		},
		updateGradient() {
			if (!this.chart) return;

			let container = this.$refs['target'];
			let linearGradient = container.querySelector('linearGradient');
			if (linearGradient) {
				linearGradient.children[0].attributes['stop-opacity'].value = '0.2';
				linearGradient.children[1].attributes['stop-opacity'].value = '0.1';
				linearGradient.children[2].attributes['stop-opacity'].value = '0';
				linearGradient.children[0].attributes['offset'].value = '0%';
				linearGradient.children[1].attributes['offset'].value = '25%';
				linearGradient.children[2].attributes['offset'].value = '50%';
			}
		},
		removeOverflowFromContainer() {
			// Caution: Do not try this at home
			// When FrappeChart is rendered inside a Card component, it adds an "overflow-auto" class.
			// This will hide chart popups that go beyond the container.
			// To fix it, we check if the parent container has that class and remove it.
			// This is a very hacky solution. You're welcome.
			if (this.$el?.parentElement?.classList.contains('overflow-auto')) {
				this.$el.parentElement.classList.remove('overflow-auto');
			}
		}
	}
};
</script>
