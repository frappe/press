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

			<Card title="Load Average">
				<FrappeChart
					type="line"
					:data="loadAverageData"
					:options="getChartOptions(d => d + ' requests')"
					:colors="[$theme.colors.green[500]]"
				/>
			</Card>
			<Card title="Disk Space">
				<FrappeChart
					type="line"
					:data="spaceData"
					:options="getChartOptions(d => d + ' jobs')"
					:colors="[$theme.colors.red[500]]"
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
			<Card title="Disk I/O">
				<FrappeChart
					type="line"
					:data="iopsData"
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
		loadavg() {
			let localTimezone = DateTime.local().zoneName;
			return {
				method: 'press.api.server.analytics',
				params: {
					name: this.server?.name,
					timezone: localTimezone,
					query: 'loadavg'
				},
				auto: true
			};
		},
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
		iops() {
			let localTimezone = DateTime.local().zoneName;
			return {
				method: 'press.api.server.analytics',
				params: {
					name: this.server?.name,
					timezone: localTimezone,
					query: 'iops'
				},
				auto: true
			};
		},
		space() {
			let localTimezone = DateTime.local().zoneName;
			return {
				method: 'press.api.server.analytics',
				params: {
					name: this.server?.name,
					timezone: localTimezone,
					query: 'space'
				},
				auto: true
			};
		}
	},
	computed: {
		loadAverageData() {
			let loadavg = this.$resources.loadavg.data;
			if (!loadavg) return;

			return {
				labels: this.formatDate(loadavg.labels),
				datasets: loadavg.datasets
			};
		},
		cpuData() {
			let cpu = this.$resources.cpu.data;
			if (!cpu) return;

			return {
				labels: this.formatDate(cpu.labels),
				datasets: cpu.datasets
			};
		},
		iopsData() {
			let iops = this.$resources.iops.data;
			if (!iops) return;

			return {
				labels: this.formatDate(iops.labels),
				datasets: iops.datasets
			};
		},
		spaceData() {
			let space = this.$resources.space.data;
			if (!space) return;

			return {
				labels: this.formatDate(space.labels),
				datasets: space.datasets
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
