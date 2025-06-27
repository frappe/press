<template>
	<div class="space-y-4">
		<div class="flex space-x-2">
			<FormControl
				class="w-40"
				label="Server"
				type="select"
				:options="serverOptions"
				v-model="chosenServer"
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
			<AnalyticsCard title="Uptime" v-if="!isServerType('Application Server')">
				<LineChart
					type="time"
					title="Uptime"
					:key="databaseUptimeData"
					:data="databaseUptimeData"
					unit="seconds"
					:chartTheme="[$theme.colors.purple[500]]"
					:loading="$resources.databaseUptime.loading"
					:error="$resources.databaseUptime.error"
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
					unit="%"
					:chartTheme="[
						$theme.colors.yellow[500], // system
						$theme.colors.cyan[500], // user
						$theme.colors.red[500], // iowait
						$theme.colors.teal[500], // irq
						$theme.colors.purple[500], // softirq
						$theme.colors.pink[500], // nice
						$theme.colors.blue[500], // steal
						$theme.colors.green[500], // idle
					]"
					:loading="$resources.cpu.loading"
					:error="$resources.cpu.error"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
				/>
			</AnalyticsCard>

			<AnalyticsCard title="Load Average">
				<LineChart
					type="time"
					title="Load Average"
					:key="loadAverageData"
					:data="loadAverageData"
					:chartTheme="[
						$theme.colors.green[500],
						$theme.colors.yellow[400],
						$theme.colors.red[500],
					]"
					:loading="$resources.loadavg.loading"
					:error="$resources.loadavg.error"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
				/>
			</AnalyticsCard>

			<AnalyticsCard title="Memory">
				<LineChart
					type="time"
					title="Memory"
					:key="memoryData"
					:data="memoryData"
					unit="bytes"
					:chartTheme="[$theme.colors.yellow[500]]"
					:loading="$resources.memory.loading"
					:error="$resources.memory.error"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
				/>
			</AnalyticsCard>

			<AnalyticsCard title="Disk Space">
				<LineChart
					type="time"
					title="Disk Space"
					:key="spaceData"
					:data="spaceData"
					unit="%"
					:chartTheme="[$theme.colors.red[500], $theme.colors.yellow[400]]"
					:loading="$resources.space.loading"
					:error="$resources.space.error"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
				/>
			</AnalyticsCard>

			<AnalyticsCard title="Network">
				<LineChart
					type="time"
					title="Network"
					:key="networkData"
					:data="networkData"
					unit="bytes"
					:chartTheme="[$theme.colors.blue[500]]"
					:loading="$resources.network.loading"
					:error="$resources.network.error"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
				/>
			</AnalyticsCard>

			<AnalyticsCard title="Disk I/O">
				<LineChart
					type="time"
					title="Disk I/O"
					:key="iopsData"
					:data="iopsData"
					unit="I0ps"
					:chartTheme="[$theme.colors.purple[500], $theme.colors.blue[500]]"
					:loading="$resources.iops.loading"
					:error="$resources.iops.error"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
				/>
			</AnalyticsCard>
		</div>
		<div
			class="!mt-6 flex w-fit cursor-pointer space-x-2"
			@click="toggleAdvancedAnalytics"
		>
			<h2 class="text-lg font-semibold">Advanced Analytics</h2>
			<FeatherIcon
				class="h-5 w-5 text-gray-500 hover:text-gray-700"
				:name="showAdvancedAnalytics ? 'chevron-down' : 'chevron-right'"
			/>
		</div>

		<!-- Advanced Analytics -->
		<div
			v-if="showAdvancedAnalytics"
			class="grid grid-cols-1 gap-5 sm:grid-cols-2"
		>
			<!-- Advanced Charts -->
			<AnalyticsCard
				v-if="isServerType('Application Server')"
				class="sm:col-span-2"
				title="Request frequency by site"
			>
				<BarChart
					title="Request frequency by site"
					:key="requestCountBySiteData"
					:data="requestCountBySiteData"
					unit="requests"
					:chartTheme="[
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
					]"
					:loading="$resources.requestCountBySite.loading"
					:error="$resources.requestCountBySite.error"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
				/>
			</AnalyticsCard>

			<AnalyticsCard
				v-if="isServerType('Application Server')"
				class="sm:col-span-2"
				title="Slowest request by site"
			>
				<BarChart
					title="Slowest request by site"
					:key="requestDurationBySiteData"
					:data="requestDurationBySiteData"
					unit="seconds"
					:chartTheme="chartColors"
					:loading="$resources.requestDurationBySite.loading"
					:error="$resources.requestDurationBySite.error"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
				/>
			</AnalyticsCard>

			<AnalyticsCard title="Queries" v-if="!isServerType('Application Server')">
				<LineChart
					type="time"
					title="Queries"
					unit="queries"
					:key="databaseCommandsCountData"
					:data="databaseCommandsCountData"
					:chartTheme="[
						$theme.colors.green[500],
						$theme.colors.red[500],
						$theme.colors.yellow[500],
						$theme.colors.pink[500],
						$theme.colors.purple[500],
						$theme.colors.blue[500],
						$theme.colors.teal[500],
						$theme.colors.cyan[500],
					]"
					:loading="$resources.databaseCommandsCount.loading"
					:error="$resources.databaseCommandsCount.error"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
				/>
			</AnalyticsCard>

			<AnalyticsCard
				title="DB Connections"
				v-if="!isServerType('Application Server')"
			>
				<LineChart
					type="time"
					title="DB Connections"
					:key="databaseConnectionsData"
					:data="databaseConnectionsData"
					unit="connections"
					:chartTheme="[
						this.$theme.colors.yellow[500],
						this.$theme.colors.green[500],
					]"
					:loading="$resources.databaseConnections.loading"
					:error="$resources.databaseConnections.error"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
				/>
			</AnalyticsCard>

			<AnalyticsCard
				title="Average Row Lock Time"
				v-if="!isServerType('Application Server')"
			>
				<LineChart
					type="time"
					title="Average Row Lock Time"
					:key="innodbAvgRowLockTimeData"
					:data="innodbAvgRowLockTimeData"
					unit="seconds"
					:chartTheme="[$theme.colors.purple[500]]"
					:loading="$resources.innodbAvgRowLockTime.loading"
					:error="$resources.innodbAvgRowLockTime.error"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
				/>
			</AnalyticsCard>

			<AnalyticsCard
				title="Buffer Pool Size"
				v-if="!isServerType('Application Server')"
			>
				<LineChart
					type="time"
					title="Buffer Pool Size"
					:key="innodbBufferPoolSizeData"
					:data="innodbBufferPoolSizeData"
					unit="bytes"
					:chartTheme="[$theme.colors.teal[500]]"
					:loading="$resources.innodbBufferPoolSize.loading"
					:error="$resources.innodbBufferPoolSize.error"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
				/>
			</AnalyticsCard>

			<AnalyticsCard
				title="Buffer Pool Size of Total Ram"
				v-if="!isServerType('Application Server')"
			>
				<LineChart
					type="time"
					title="Buffer Pool Size of Total Ram"
					:key="innodbBufferPoolSizeOfTotalRamData"
					:data="innodbBufferPoolSizeOfTotalRamData"
					unit="%"
					:chartTheme="[$theme.colors.cyan[500]]"
					:loading="$resources.innodbBufferPoolSizeOfTotalRam.loading"
					:error="$resources.innodbBufferPoolSizeOfTotalRam.error"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
				/>
				<template #action>
					<router-link
						class="text-base text-gray-600 hover:text-gray-700"
						:to="{
							name: 'Server Detail Actions',
							params: { name: this.serverName },
						}"
					>
						Manage InnoDB Buffer →
					</router-link>
				</template>
			</AnalyticsCard>

			<AnalyticsCard
				title="Buffer Pool Miss Percent"
				v-if="!isServerType('Application Server')"
			>
				<LineChart
					type="time"
					title="Buffer Pool Miss Percent"
					:key="innodbBufferPoolMissPercentageData"
					:data="innodbBufferPoolMissPercentageData"
					unit="%"
					:chartTheme="[$theme.colors.orange[500]]"
					:loading="$resources.innodbBufferPoolMissPercentage.loading"
					:error="$resources.innodbBufferPoolMissPercentage.error"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
				/>
				<template #action>
					<router-link
						class="text-base text-gray-600 hover:text-gray-700"
						:to="{
							name: 'Server Detail Actions',
							params: { name: this.serverName },
						}"
					>
						Manage InnoDB Buffer →
					</router-link>
				</template>
			</AnalyticsCard>

			<AnalyticsCard
				v-if="!isServerType('Application Server')"
				class="sm:col-span-2"
				title="Frequent Slow queries"
			>
				<template #action>
					<TabButtons
						:buttons="[{ label: 'Denormalized' }, { label: 'Normalized' }]"
						v-model="slowLogsFrequencyType"
					/>
				</template>
				<BarChart
					title="Frequent Slow queries"
					:key="slowLogsCountData"
					:data="slowLogsCountData"
					unit="queries"
					:chartTheme="chartColors"
					:loading="$resources.slowLogsCount.loading"
					:error="$resources.slowLogsCount.error"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
				/>
			</AnalyticsCard>

			<AnalyticsCard
				v-if="!isServerType('Application Server')"
				class="sm:col-span-2"
				title="Slowest queries"
			>
				<template #action>
					<TabButtons
						:buttons="[{ label: 'Denormalized' }, { label: 'Normalized' }]"
						v-model="slowLogsDurationType"
					/>
				</template>
				<BarChart
					title="Slowest queries"
					:key="slowLogsDurationData"
					:data="slowLogsDurationData"
					unit="seconds"
					:chartTheme="chartColors"
					:loading="$resources.slowLogsDuration.loading"
					:error="$resources.slowLogsDuration.error"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
				/>
			</AnalyticsCard>
		</div>
	</div>
</template>

<script>
import { getCachedDocumentResource } from 'frappe-ui';
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
			duration: '1 Hour',
			showAdvancedAnalytics: false,
			localTimezone: dayjs.tz.guess(),
			slowLogsDurationType: 'Denormalized',
			slowLogsFrequencyType: 'Denormalized',
			chosenServer: this.$route.query.server ?? this.serverName,
			durationOptions: ['1 Hour', '6 Hour', '24 Hour', '7 Days', '15 Days'],
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
		chosenServer() {
			this.$router.push({
				query: {
					server: this.chosenServer,
				},
			});
		},
	},
	resources: {
		loadavg() {
			return {
				url: 'press.api.server.analytics',
				params: {
					name: this.chosenServer,
					timezone: this.localTimezone,
					query: 'loadavg',
					duration: this.duration,
				},
				auto: true,
			};
		},
		cpu() {
			return {
				url: 'press.api.server.analytics',
				params: {
					name: this.chosenServer,
					timezone: this.localTimezone,
					query: 'cpu',
					duration: this.duration,
				},
				auto: true,
			};
		},
		memory() {
			return {
				url: 'press.api.server.analytics',
				params: {
					name: this.chosenServer,
					timezone: this.localTimezone,
					query: 'memory',
					duration: this.duration,
				},
				auto: true,
			};
		},
		network() {
			return {
				url: 'press.api.server.analytics',
				params: {
					name: this.chosenServer,
					timezone: this.localTimezone,
					query: 'network',
					duration: this.duration,
				},
				auto: true,
			};
		},
		iops() {
			return {
				url: 'press.api.server.analytics',
				params: {
					name: this.chosenServer,
					timezone: this.localTimezone,
					query: 'iops',
					duration: this.duration,
				},
				auto: true,
			};
		},
		space() {
			return {
				url: 'press.api.server.analytics',
				params: {
					name: this.chosenServer,
					timezone: this.localTimezone,
					query: 'space',
					duration: this.duration,
				},
				auto: true,
			};
		},
		requestCountBySite() {
			return {
				url: 'press.api.server.get_request_by_site',
				params: {
					name: this.chosenServer,
					query: 'count',
					timezone: this.localTimezone,
					duration: this.duration,
				},
				auto:
					this.showAdvancedAnalytics && this.isServerType('Application Server'),
			};
		},
		requestDurationBySite() {
			return {
				url: 'press.api.server.get_request_by_site',
				params: {
					name: this.chosenServer,
					query: 'duration',
					timezone: this.localTimezone,
					duration: this.duration,
				},
				auto:
					this.showAdvancedAnalytics && this.isServerType('Application Server'),
			};
		},
		slowLogsCount() {
			return {
				url: 'press.api.server.get_slow_logs_by_site',
				params: {
					name: this.chosenServer,
					query: 'count',
					timezone: this.localTimezone,
					duration: this.duration,
					normalize: this.slowLogsFrequencyType === 'Normalized',
				},
				auto:
					this.showAdvancedAnalytics &&
					!this.isServerType('Application Server'),
			};
		},
		slowLogsDuration() {
			return {
				url: 'press.api.server.get_slow_logs_by_site',
				params: {
					name: this.chosenServer,
					query: 'duration',
					timezone: this.localTimezone,
					duration: this.duration,
					normalize: this.slowLogsDurationType === 'Normalized',
				},
				auto:
					this.showAdvancedAnalytics &&
					!this.isServerType('Application Server'),
			};
		},
		databaseUptime() {
			return {
				url: 'press.api.server.analytics',
				params: {
					name: this.chosenServer,
					timezone: this.localTimezone,
					query: 'database_uptime',
					duration: this.duration,
				},
				auto: this.isServerType('Database Server'),
			};
		},
		databaseCommandsCount() {
			return {
				url: 'press.api.server.analytics',
				params: {
					name: this.chosenServer,
					timezone: this.localTimezone,
					query: 'database_commands_count',
					duration: this.duration,
				},
				auto:
					this.showAdvancedAnalytics && this.isServerType('Database Server'),
			};
		},
		databaseConnections() {
			return {
				url: 'press.api.server.analytics',
				params: {
					name: this.chosenServer,
					timezone: this.localTimezone,
					query: 'database_connections',
					duration: this.duration,
				},
				auto:
					this.showAdvancedAnalytics && this.isServerType('Database Server'),
			};
		},
		innodbBufferPoolSize() {
			return {
				url: 'press.api.server.analytics',
				params: {
					name: this.chosenServer,
					timezone: this.localTimezone,
					query: 'innodb_bp_size',
					duration: this.duration,
				},
				auto:
					this.showAdvancedAnalytics && this.isServerType('Database Server'),
			};
		},
		innodbBufferPoolSizeOfTotalRam() {
			return {
				url: 'press.api.server.analytics',
				params: {
					name: this.chosenServer,
					timezone: this.localTimezone,
					query: 'innodb_bp_size_of_total_ram',
					duration: this.duration,
				},
				auto:
					this.showAdvancedAnalytics && this.isServerType('Database Server'),
			};
		},
		innodbBufferPoolMissPercentage() {
			return {
				url: 'press.api.server.analytics',
				params: {
					name: this.chosenServer,
					timezone: this.localTimezone,
					query: 'innodb_bp_miss_percent',
					duration: this.duration,
				},
				auto:
					this.showAdvancedAnalytics && this.isServerType('Database Server'),
			};
		},
		innodbAvgRowLockTime() {
			return {
				url: 'press.api.server.analytics',
				params: {
					name: this.chosenServer,
					timezone: this.localTimezone,
					query: 'innodb_avg_row_lock_time',
					duration: this.duration,
				},
				auto:
					this.showAdvancedAnalytics && this.isServerType('Database Server'),
			};
		},
	},
	computed: {
		$server() {
			return getCachedDocumentResource('Server', this.serverName);
		},
		serverOptions() {
			return [
				{
					label: 'Application Server',
					value: this.$server.doc.name,
				},
				{
					label: 'Database Server',
					value: this.$server.doc.database_server,
				},
				{
					label: 'Replication Server',
					value: this.$server.doc.replication_server,
				},
			].filter((v) => v.value);
		},
		loadAverageData() {
			let loadavg = this.$resources.loadavg.data;
			if (!loadavg) return;

			loadavg.datasets.sort(
				(a, b) => Number(a.name.split(' ')[2]) - Number(b.name.split(' ')[2]),
			);

			return this.transformMultiLineChartData(loadavg);
		},
		cpuData() {
			let cpu = this.$resources.cpu.data;
			if (!cpu) return;
			const order = [
				'system',
				'user',
				'iowait',
				'irq',
				'softirq',
				'nice',
				'steal',
				'idle',
			];

			cpu.datasets = cpu.datasets.sort((a, b) => {
				return order.indexOf(a.name) - order.indexOf(b.name);
			});

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

			return this.transformMultiLineChartData(iops);
		},
		spaceData() {
			let space = this.$resources.space.data;
			if (!space) return;

			return this.transformMultiLineChartData(space);
		},
		networkData() {
			let network = this.$resources.network.data;
			if (!network) return;

			return this.transformSingleLineChartData(network);
		},
		requestCountBySiteData() {
			const requests = this.$resources.requestCountBySite.data;
			if (!requests) return;

			return requests;
		},
		requestDurationBySiteData() {
			const requests = this.$resources.requestDurationBySite.data;
			if (!requests) return;

			return requests;
		},
		slowLogsDurationData() {
			const slowLogs = this.$resources.slowLogsDuration.data;
			if (!slowLogs) return;

			return slowLogs;
		},
		slowLogsCountData() {
			const slowLogs = this.$resources.slowLogsCount.data;
			if (!slowLogs) return;

			return slowLogs;
		},
		databaseUptimeData() {
			const uptime = this.$resources.databaseUptime.data;
			if (!uptime) return;

			return this.transformSingleLineChartData(uptime);
		},
		databaseCommandsCountData() {
			const commandsCount = this.$resources.databaseCommandsCount.data;
			if (!commandsCount) return;

			return this.transformMultiLineChartData(commandsCount, null, false);
		},
		databaseConnectionsData() {
			const connections = this.$resources.databaseConnections.data;
			if (!connections) return;

			return this.transformMultiLineChartData(connections, null, false);
		},
		innodbBufferPoolSizeData() {
			let innodbBufferPoolSize = this.$resources.innodbBufferPoolSize.data;
			if (!innodbBufferPoolSize) return;

			return this.transformSingleLineChartData(innodbBufferPoolSize, false);
		},
		innodbBufferPoolSizeOfTotalRamData() {
			let data = this.$resources.innodbBufferPoolSizeOfTotalRam.data;
			if (!data) return;
			let payload = this.transformSingleLineChartData(data, true);
			payload['markLine'] = {
				data: [
					{
						name: 'Too Low InnoDB Buffer Pool',
						yAxis: 15,
						label: {
							formatter: '{b} ({c}%)',
							position: 'middle',
						},
						lineStyle: {
							color: '#f5222d',
						},
					},
					{
						name: 'Too High InnoDB Buffer Pool',
						yAxis: 65,
						label: {
							formatter: '{b} ({c}%)',
							position: 'middle',
						},
						lineStyle: {
							color: '#f5222d',
						},
					},
				],
				symbol: ['none', 'none'],
			};
			return payload;
		},
		innodbBufferPoolMissPercentageData() {
			let data = this.$resources.innodbBufferPoolMissPercentage.data;
			if (!data) return;
			let payload = this.transformSingleLineChartData(data, false);
			payload['markLine'] = {
				data: [
					{
						name: 'Accepted Range',
						yAxis: 1,
						label: {
							formatter: '{b} < {c}%',
							position: 'middle',
						},
						lineStyle: {
							color: '#f5222d',
						},
					},
				],
				symbol: ['none', 'none'],
			};
			return payload;
		},
		innodbAvgRowLockTimeData() {
			let data = this.$resources.innodbAvgRowLockTime.data;
			if (!data) return;
			return this.transformSingleLineChartData(data, false);
		},
	},
	methods: {
		transformSingleLineChartData(data, percentage = false) {
			if (!data.datasets?.length) return;

			let dataset = [];
			const name = data.datasets ? data.datasets[0]?.name : null;
			for (let index = 0; index < data.datasets[0].values.length; index++) {
				dataset.push([
					+new Date(data.labels[index]),
					data.datasets[0].values[index],
				]);
			}

			return {
				datasets: [{ dataset: dataset, name }],
				yMax: percentage ? 100 : null,
			};
		},
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
		isServerType(type) {
			return (
				this.chosenServer ===
				this.serverOptions.find((s) => s.label === type)?.value
			);
		},
		toggleAdvancedAnalytics() {
			this.showAdvancedAnalytics = !this.showAdvancedAnalytics;
		},
	},
};
</script>
