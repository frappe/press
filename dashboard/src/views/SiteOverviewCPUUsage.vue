<template>
	<Card title="CPU Usage">
		<div v-show="requestCounter.data.length" ref="target"></div>
		<div
			v-show="requestCounter.data.length == 0"
			class="flex items-center justify-center py-20 text-base text-gray-700"
		>
			No data yet
		</div>
	</Card>
</template>
<script>
import { DateTime } from 'luxon';
import { Chart } from 'frappe-charts/dist/frappe-charts.esm.js';

export default {
	name: 'CPUUsage',
	props: ['site'],
	resources: {
		requestCounter() {
			return {
				method: 'press.api.analytics.request_counter',
				params: {
					name: this.site.name
				},
				default: { data: [], plan_limit: 0 },
				onSuccess(data) {
					if (data.data.length > 0) {
						this.makeChart();
					}
				}
			};
		}
	},
	mounted() {
		this.$resources.requestCounter.fetch();
	},
	computed: {
		requestCounter() {
			return this.$resources.requestCounter.data;
		}
	},
	methods: {
		makeChart() {
			let { data, plan_limit } = this.requestCounter;
			this.chart = new Chart(this.$refs['target'], {
				data: {
					labels: data.map(d => {
						return {
							timestamp: d.timestamp,
							toString() {
								return DateTime.fromSQL(d.timestamp).toFormat('hh:mm a');
							}
						};
					}),
					datasets: [
						{
							values: data.map(d => d.value / 1000000)
						}
					],
					yMarkers: [{ label: 'Daily CPU Time Limit', value: plan_limit }]
				},
				type: 'line',
				colors: ['blue'],
				axisOptions: {
					xIsSeries: true,
					shortenYAxisNumbers: 1
				},
				lineOptions: {
					hideDots: true,
					spline: true
				},
				tooltipOptions: {
					formatTooltipX: d => {
						return DateTime.fromSQL(d.timestamp).toFormat('dd-MM-yyyy hh:mm a');
					},
					formatTooltipY: d => {
						return d + ' s';
					}
				}
			});
		}
	}
};
</script>
