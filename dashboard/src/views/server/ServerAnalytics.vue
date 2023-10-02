<template>
	<div class="space-y-4">
		<div class="grid justify-items-stretch">
			<label>
				<span class="mb-2 inline-block text-sm leading-4 text-gray-700">
					Duration
				</span>
				<select class="form-select ml-2" v-model="duration">
					<option v-for="option in durationOptions" :key="option">
						{{ option }}
					</option>
				</select>
			</label>
		</div>
		<div
			v-if="cpuData?.datasets?.length"
			class="grid grid-cols-1 gap-5 sm:grid-cols-2"
		>
			<Card title="CPU">
				<FrappeChart
					type="line"
					:data="cpuData"
					:options="getChartOptions(d => d + ' %')"
					:colors="[$theme.colors.yellow[500]]"
				/>
			</Card>

			<Card title="Load Average">
				<FrappeChart
					type="line"
					:data="loadAverageData"
					:options="getChartOptions(d => d)"
					:colors="[$theme.colors.green[500]]"
				/>
			</Card>

			<Card title="Memory">
				<FrappeChart
					type="line"
					:data="memoryData"
					:options="getChartOptions(d => formatBytes(d))"
					:colors="[$theme.colors.yellow[500]]"
				/>
			</Card>

			<Card title="Disk Space">
				<FrappeChart
					type="line"
					:data="spaceData"
					:options="getChartOptions(d => d + ' %')"
					:colors="[$theme.colors.red[500]]"
				/>
			</Card>
			<Card title="Network">
				<FrappeChart
					type="line"
					:data="networkData"
					:options="getChartOptions(d => formatBytes(d))"
					:colors="[$theme.colors.blue[500]]"
				/>
			</Card>
			<Card title="Disk I/O">
				<FrappeChart
					type="line"
					:data="iopsData"
					:options="getChartOptions(d => d + ' I0ps')"
					:colors="[$theme.colors.blue[500]]"
				/>
			</Card>
		</div>
		<div
			v-if="!$resources.cpu.loading && !cpuData?.datasets?.length"
			class="text-base text-gray-600"
		>
			No data yet
		</div>
	</div>
</template>

<script>
import { DateTime } from 'luxon';
import FrappeChart from '@/components/FrappeChart.vue';

export default {
	name: 'ServerAnalytics',
	props: ['server', 'serverName'],
	components: {
		FrappeChart
	},
	data() {
		return {
			duration: '1 Hour',
			durationOptions: ['1 Hour', '6 Hour', '24 Hour', '7 Days', '15 Days']
		};
	},
	resources: {
		loadavg() {
			let localTimezone = DateTime.local().zoneName;
			return {
				url: 'press.api.server.analytics',
				params: {
					name: this.serverName,
					timezone: localTimezone,
					query: 'loadavg',
					duration: this.duration
				},
				auto: true
			};
		},
		cpu() {
			let localTimezone = DateTime.local().zoneName;
			return {
				url: 'press.api.server.analytics',
				params: {
					name: this.serverName,
					timezone: localTimezone,
					query: 'cpu',
					duration: this.duration
				},
				auto: true
			};
		},
		memory() {
			let localTimezone = DateTime.local().zoneName;
			return {
				url: 'press.api.server.analytics',
				params: {
					name: this.serverName,
					timezone: localTimezone,
					query: 'memory',
					duration: this.duration
				},
				auto: true
			};
		},
		network() {
			let localTimezone = DateTime.local().zoneName;
			return {
				url: 'press.api.server.analytics',
				params: {
					name: this.serverName,
					timezone: localTimezone,
					query: 'network',
					duration: this.duration
				},
				auto: true
			};
		},
		iops() {
			let localTimezone = DateTime.local().zoneName;
			return {
				url: 'press.api.server.analytics',
				params: {
					name: this.serverName,
					timezone: localTimezone,
					query: 'iops',
					duration: this.duration
				},
				auto: true
			};
		},
		space() {
			let localTimezone = DateTime.local().zoneName;
			return {
				url: 'press.api.server.analytics',
				params: {
					name: this.serverName,
					timezone: localTimezone,
					query: 'space',
					duration: this.duration
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
		memoryData() {
			let memory = this.$resources.memory.data;
			if (!memory) return;

			return {
				labels: this.formatDate(memory.labels),
				datasets: memory.datasets
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
