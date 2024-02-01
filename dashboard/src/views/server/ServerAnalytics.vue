<template>
	<div class="space-y-4">
		<FormControl
			class="w-32"
			label="Duration"
			type="select"
			:options="
				durationOptions.map(option => ({ label: option, value: option }))
			"
			v-model="duration"
		/>
		<div class="grid grid-cols-1 gap-5 sm:grid-cols-2">
			<LineChart
				type="time"
				title="CPU"
				:key="cpuData"
				:data="cpuData"
				unit="%"
				:chartTheme="[
					$theme.colors.green[500], // idle
					$theme.colors.red[500], // iowait
					$theme.colors.yellow[500], // irq
					$theme.colors.pink[500], // nice
					$theme.colors.purple[500], // softirq
					$theme.colors.blue[500], // steal
					$theme.colors.teal[500], // system
					$theme.colors.cyan[500] // user
				]"
				:loading="$resources.cpu.loading"
				:error="$resources.cpu.error"
			/>

			<LineChart
				type="time"
				title="Load Average"
				:key="loadAverageData"
				:data="loadAverageData"
				:loading="$resources.loadavg.loading"
				:error="$resources.loadavg.error"
			/>

			<LineChart
				type="time"
				title="Memory"
				:key="memoryData"
				:data="memoryData"
				unit="bytes"
				:chartTheme="[$theme.colors.yellow[500]]"
				:loading="$resources.memory.loading"
				:error="$resources.memory.error"
			/>

			<LineChart
				type="time"
				title="Disk Space"
				:key="spaceData"
				:data="spaceData"
				unit="%"
				:chartTheme="[$theme.colors.red[500]]"
				:loading="$resources.space.loading"
				:error="$resources.space.error"
			/>

			<LineChart
				type="time"
				title="Network"
				:key="networkData"
				:data="networkData"
				unit="bytes"
				:chartTheme="[$theme.colors.blue[500]]"
				:loading="$resources.network.loading"
				:error="$resources.network.error"
			/>
			<LineChart
				type="time"
				title="Disk I/O"
				:key="iopsData"
				:data="iopsData"
				unit="I0ps"
				:chartTheme="[$theme.colors.purple[500]]"
				:loading="$resources.iops.loading"
				:error="$resources.iops.error"
			/>
		</div>
	</div>
</template>

<script>
import { DateTime } from 'luxon';
import LineChart from '@/components/charts/LineChart.vue';

export default {
	name: 'ServerAnalytics',
	props: ['serverName'],
	components: {
		LineChart
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

			return this.transformMultiLineChartData(loadavg);
		},
		cpuData() {
			let cpu = this.$resources.cpu.data;
			if (!cpu) return;

			return this.transformMultiLineChartData(cpu, 'cpu', true);
		},
		memoryData() {
			let memory = this.$resources.memory.data;
			if (!memory) return;

			return this.transformSingleLineChartData(memory);
		},
		iopsData() {
			let iops = this.$resources.iops.data;
			if (!iops) return;

			return this.transformSingleLineChartData(iops);
		},
		spaceData() {
			let space = this.$resources.space.data;
			if (!space) return;

			return this.transformSingleLineChartData(space, true);
		},
		networkData() {
			let network = this.$resources.network.data;
			if (!network) return;

			return this.transformSingleLineChartData(network);
		}
	},
	methods: {
		transformSingleLineChartData(data, percentage = false) {
			let dataset = [];
			const name = data.datasets ? data.datasets[0]?.name : null;
			for (let index = 0; index < data.datasets[0].values.length; index++) {
				dataset.push([
					+new Date(data.labels[index]),
					data.datasets[0].values[index]
				]);
			}

			return {
				datasets: [{ dataset: dataset, name }],
				yMax: percentage ? 100 : null
			};
		},
		transformMultiLineChartData(data, stack = null, percentage = false) {
			let total = [];
			if (percentage) {
				// the sum of each cpu values tends to differ by few values
				// so we need to calculate the total for each timestamp
				for (let i = 0; i < data.datasets[0].values.length; i++) {
					for (let j = 0; j < data.datasets.length; j++) {
						if (!total[i]) total[i] = 0;
						total[i] += data.datasets[j].values[i];
					}
				}
			}
			const datasets = data.datasets.map(({ name, values }) => {
				let dataset = [];
				for (let i = 0; i < values.length; i++) {
					dataset.push([
						+new Date(data.labels[i]),
						percentage ? (values[i] / total[i]) * 100 : values[i]
					]);
				}
				return { name, dataset, stack };
			});

			return { datasets, yMax: percentage ? 100 : null };
		}
	}
};
</script>
