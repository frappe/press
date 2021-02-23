<template>
	<div ref="target"></div>
</template>
<script>
import { Chart } from 'frappe-charts/dist/frappe-charts.esm.js';
export default {
	name: 'FrappeChart',
	props: ['type', 'data', 'options', 'colors'],
	destroyed() {
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
		}
	}
};
</script>
