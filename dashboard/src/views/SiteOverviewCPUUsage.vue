<template>
	<Card title="Daily usage">
		<template #actions>
			<router-link
				class="text-base text-blue-500 hover:text-blue-600"
				:to="`/sites/${site.name}/analytics`"
			>
				All analytics →
			</router-link>
		</template>
		<div v-show="requestCounter.data.length" ref="target"></div>
		<div
			v-show="requestCounter.data.length == 0"
			class="flex items-center justify-center py-20 text-base text-gray-700"
		>
			<Button
				v-if="$resources.requestCounter.loading"
				:loading="true"
				loading-text="Loading"
			/>
			<span v-else> No data yet </span>
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
			let localTimezone = DateTime.local().zoneName;
			return {
				method: 'press.api.analytics.daily_usage',
				params: { name: this.site.name, timezone: localTimezone },
				default: { data: [], plan_limit: 0 },
				onSuccess(data) {
					if (data.data.length > 0) {
						this.$nextTick().then(() => this.makeChart());
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
			let values = data.map(d => d.value / 1000000);

			this.chart = new Chart(this.$refs['target'], {
				data: {
					labels: data.map(d => {
						return {
							date: d.date,
							toString() {
								return DateTime.fromSQL(d.date).toFormat('d MMM');
							}
						};
					}),
					datasets: [{ values }],
					// show daily limit marker if usage crosses 50%
					yMarkers: values.some(value => value > plan_limit / 2)
						? [{ label: 'Daily CPU Time Limit', value: plan_limit }]
						: null
				},
				type: 'line',
				colors: [this.$theme.colors.purple[500]],
				axisOptions: {
					xIsSeries: true,
					shortenYAxisNumbers: 1
				},
				lineOptions: {
					hideDots: true
				},
				tooltipOptions: {
					formatTooltipX: d => {
						return DateTime.fromSQL(d.date).toLocaleString();
					},
					formatTooltipY: d => {
						return this.round(d, 1) + ' sec';
					}
				}
			});
		}
	}
};
</script>
