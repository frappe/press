<template>
	<div class="space-y-4">
		<div class="grid grid-cols-1 gap-5 sm:grid-cols-2">
			<Card title="CPU">
				<FrappeChart
					type="line"
					:data="cpuData"
					:options="getChartOptions(d => d + ' s')"
					:colors="[$theme.colors.yellow[500]]"
				/>
			</Card>
			<Card title="Network">
				<FrappeChart
					type="line"
					:data="networkData"
					:options="getChartOptions(d => d + ' s')"
					:colors="[$theme.colors.blue[500]]"
				/>
			</Card>
		</div>
	</div>
</template>

<script>
import { DateTime } from 'luxon';
import FrappeChart from '@/components/FrappeChart.vue';

export default {
	name: 'ServerAnalytics',
	props: ['server'],
	components: {
		FrappeChart
	},
	resources: {
		cpu() {
			let localTimezone = DateTime.local().zoneName;
			return {
				method: 'press.api.server.analytics',
				params: {
					name: this.server?.name,
					timezone: localTimezone,
					query: 'cpu'
				},
				auto: true
			};
		},
		network() {
			let localTimezone = DateTime.local().zoneName;
			return {
				method: 'press.api.server.analytics',
				params: {
					name: this.server?.name,
					timezone: localTimezone,
					query: 'network'
				},
				auto: true
			};
		},
	},
	computed: {
		cpuData() {
			let cpu = this.$resources.cpu.data;
			if (!cpu) return;

			return {
				labels: this.formatDate(cpu.labels),
				datasets: cpu.datasets
			};
		},
		networkData() {
			let network = this.$resources.network.data;
			if (!network) return;

			return {
				labels: this.formatDate(network.labels),
				datasets: network.datasets
			};
		}
	},
	methods: {
		getChartOptions(yFormatter) {
			return {
				axisOptions: {
					xIsSeries: true,
					shortenYAxisNumbers: 1
				},
				lineOptions: {
					hideDots: true,
					regionFill: true
				},
				tooltipOptions: {
					formatTooltipX: d => {
						return DateTime.fromSQL(d.date).toLocaleString(
							DateTime.DATETIME_MED
						);
					},
					formatTooltipY: yFormatter
				}
			};
		},
		formatDate(labels) {
			return labels.map(date => ({
				date: date,
				toString: () => DateTime.fromSQL(date).toFormat('d MMM')
			}));
		}
	}
};
</script>
