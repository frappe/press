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
		<div class="grid grid-cols-1 gap-5 sm:grid-cols-2">
			<LineChart
				type="time"
				title="CPU"
				:key="cpuData"
				:data="cpuData"
				unit="%"
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
	props: ['server', 'serverName'],
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

			return this.transformMultiLineChartData(cpu);
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

			return this.transformSingleLineChartData(space);
		},
		networkData() {
			let network = this.$resources.network.data;
			if (!network) return;

			return this.transformSingleLineChartData(network);
		}
	},
	methods: {
		transformSingleLineChartData(data) {
			let datasets = [];
			for (let index = 0; index < data.datasets[0].values.length; index++) {
				datasets.push([
					+new Date(data.labels[index]),
					data.datasets[0].values[index]
				]);
			}

			return { datasets: [datasets] };
		},
		transformMultiLineChartData(data) {
			const datasets = data.datasets.map(({ name, values }) => {
				let dataset = [];
				for (let i = 0; i < values.length; i++) {
					dataset.push([+new Date(data.labels[i]), values[i]]);
				}
				return { name, dataset };
			});

			return { datasets };
		}
	}
};
</script>
