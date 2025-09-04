<template>
	<div class="space-y-4">
		<div class="flex space-x-2">
			<FormControl
				class="w-40"
				label="Bench Group"
				type="select"
				:options="releaseGroupOptions"
				v-model="chosenGroup"
			/>
			<FormControl
				class="w-32"
				label="Duration"
				type="select"
				:options="
					durationOptions.map((option) => ({ label: option, value: option }))
				"
				v-model="duration"
			/>
		</div>
		<div class="grid grid-cols-1 gap-5 sm:grid-cols-2">
			<AnalyticsCard title="Memory">
				<LineChart
					type="time"
					title="Memory"
					:key="memoryData"
					:data="memoryData"
					unit="GB"
					:chartTheme="$data.chartColors"
					:loading="$resources.memory.loading"
					:error="$resources.memory.error"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
				/>
			</AnalyticsCard>
			<AnalyticsCard title="CPU">
				<LineChart
					type="time"
					title="CPU"
					:key="cpuData"
					:data="cpuData"
					unit="seconds"
					:chartTheme="$data.chartColors"
					:loading="$resources.cpu.loading"
					:error="$resources.cpu.error"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
				/>
			</AnalyticsCard>
		</div>
		<div class="grid grid-cols-1 gap-5 sm:grid-cols-2">
			<AnalyticsCard title="Incoming Network">
				<LineChart
					type="time"
					title="Memory"
					:key="incomingNetwork"
					:data="incomingNetwork"
					unit="bytes"
					:chartTheme="$data.chartColors"
					:loading="$resources.incomingNetwork.loading"
					:error="$resources.incomingNetwork.error"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
				/>
			</AnalyticsCard>
			<AnalyticsCard title="Outgoing Network">
				<LineChart
					type="time"
					title="CPU"
					:key="outgoingNetwork"
					:data="outgoingNetwork"
					unit="bytes"
					:chartTheme="$data.chartColors"
					:loading="$resources.outgoingNetwork.loading"
					:error="$resources.outgoingNetwork.error"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
				/>
			</AnalyticsCard>
		</div>
		<div class="grid grid-cols-1 gap-5 sm:grid-cols-2">
			<AnalyticsCard title="Read Bytes">
				<LineChart
					type="time"
					title="Memory"
					:key="readBytesFs"
					:data="readBytesFs"
					unit="bytes"
					:chartTheme="$data.chartColors"
					:loading="$resources.readBytesFs.loading"
					:error="$resources.readBytesFs.error"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
				/>
			</AnalyticsCard>
			<AnalyticsCard title="Write Bytes">
				<LineChart
					type="time"
					title="CPU"
					:key="writeBytesFs"
					:data="writeBytesFs"
					unit="bytes"
					:chartTheme="$data.chartColors"
					:loading="$resources.writeBytesFs.loading"
					:error="$resources.writeBytesFs.error"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
				/>
			</AnalyticsCard>
		</div>
	</div>
</template>

<script>
import LineChart from '@/components/charts/LineChart.vue';
import BarChart from '@/components/charts/BarChart.vue';
import AnalyticsCard from '../site/AnalyticsCard.vue';
import dayjs from '../../utils/dayjs';

export default {
	props: ['serverName'],
	components: {
		AnalyticsCard,
		BarChart,
		LineChart,
	},
	data() {
		return {
			duration: '1h',
			localTimezone: dayjs.tz.guess(),
			chosenGroup: this.$route.query.group ?? '',
			durationOptions: ['1h', '6h', '24h', '7d', '15d'],
			chartColors: [
				this.$theme.colors.green[500],
				this.$theme.colors.red[500],
				this.$theme.colors.yellow[500],
				this.$theme.colors.pink[500],
				this.$theme.colors.purple[500],
				this.$theme.colors.blue[500],
				this.$theme.colors.teal[500],
				this.$theme.colors.cyan[500],
				this.$theme.colors.gray[500],
				this.$theme.colors.orange[500],
			],
		};
	},
	watch: {
		chosenGroup() {
			this.$router.push({
				query: {
					group: this.chosenGroup,
				},
			});
		},
	},
	resources: {
		memory() {
			return {
				url: 'press.api.analytics.get_memory_usage',
				params: {
					group: this.chosenGroup,
					timezone: this.localTimezone,
					duration: this.duration,
				},
				auto: true,
			};
		},
		cpu() {
			return {
				url: 'press.api.analytics.get_cpu_usage',
				params: {
					group: this.chosenGroup,
					timezone: this.localTimezone,
					duration: this.duration,
				},
				auto: true,
			};
		},
		incomingNetwork() {
			return {
				url: 'press.api.analytics.get_incoming_network_traffic',
				params: {
					group: this.chosenGroup,
					timezone: this.localTimezone,
					duration: this.duration,
				},
				auto: true,
			};
		},
		outgoingNetwork() {
			return {
				url: 'press.api.analytics.get_outgoing_network_traffic',
				params: {
					group: this.chosenGroup,
					timezone: this.localTimezone,
					duration: this.duration,
				},
				auto: true,
			};
		},
		readBytesFs() {
			return {
				url: 'press.api.analytics.get_fs_read_bytes',
				params: {
					group: this.chosenGroup,
					timezone: this.localTimezone,
					duration: this.duration,
				},
				auto: true,
			};
		},
		writeBytesFs() {
			return {
				url: 'press.api.analytics.get_fs_write_bytes',
				params: {
					group: this.chosenGroup,
					timezone: this.localTimezone,
					duration: this.duration,
				},
				auto: true,
			};
		},
		groups() {
			return {
				url: 'press.api.client.get_list',
				params: {
					doctype: 'Release Group',
					fields: ['title', 'name'],
					filters: { server: this.serverName, enabled: 1 },
				},
				auto: true,
			};
		},
	},
	computed: {
		releaseGroupOptions() {
			let groups = this.$resources.groups.data;

			if (!groups) {
				return null;
			}

			return groups
				.filter((group) => group.active_benches > 0)
				.map((group) => ({
					label: group.title,
					value: group.name,
				}));
		},
		memoryData() {
			let memory = this.$resources.memory.data?.memory;
			if (!memory) return;

			return this.transformMultiLineChartData(memory);
		},
		cpuData() {
			let cpu = this.$resources.cpu.data?.cpu;
			if (!cpu) return;

			return this.transformMultiLineChartData(cpu);
		},
		incomingNetwork() {
			let traffic =
				this.$resources.incomingNetwork.data?.network_traffic_inward;
			if (!traffic) return;

			return this.transformMultiLineChartData(traffic);
		},
		outgoingNetwork() {
			let network_traffic_outward =
				this.$resources.outgoingNetwork.data?.network_traffic_outward;
			if (!network_traffic_outward) return;

			return this.transformMultiLineChartData(network_traffic_outward);
		},
		readBytesFs() {
			let read_bytes_fs = this.$resources.readBytesFs.data?.read_bytes_fs;
			if (!read_bytes_fs) return;

			return this.transformMultiLineChartData(read_bytes_fs);
		},
		writeBytesFs() {
			let write_bytes_fs = this.$resources.writeBytesFs.data?.write_bytes_fs;
			if (!write_bytes_fs) return;

			return this.transformMultiLineChartData(write_bytes_fs);
		},
	},
	methods: {
		transformMultiLineChartData(data, stack = null, percentage = false) {
			if (!data.datasets?.length) return;

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
						percentage ? (values[i] / total[i]) * 100 : values[i],
					]);
				}
				return { name, dataset, stack };
			});

			return { datasets, yMax: percentage ? 100 : null };
		},
	},
};
</script>
