<template>
	<div class="space-y-4">
		<div class="flex space-x-2">
			<!-- <FormControl
				class="w-40"
				label="Server"
				type="select"
				:options="serverOptions"
				v-model="chosenBench"
			/> -->
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
					unit="bytes"
					:chartTheme="[$theme.colors.yellow[500]]"
					:loading="$resources.cadvisor.loading"
					:error="$resources.cadvisor.error"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
				/>
			</AnalyticsCard>

			<!-- <AnalyticsCard title="Disk Space">
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
			</AnalyticsCard> -->

			<!-- <AnalyticsCard title="Disk I/O">
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
			</AnalyticsCard> -->
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
	props: ['benchName'],
	components: {
		AnalyticsCard,
		BarChart,
		LineChart,
	},
	data() {
		return {
			duration: '1h',
			localTimezone: dayjs.tz.guess(),
			chosenBench: this.$route.query.bench ?? this.benchName,
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
		chosenBench() {
			this.$router.push({
				query: {
					server: this.chosenBench,
				},
			});
		},
	},
	resources: {
		cadvisor() {
			return {
				url: 'press.api.analytics.cadvisor',
				params: {
					bench: this.chosenBench,
					timezone: this.localTimezone,
					duration: this.duration,
				},
				auto: true,
			};
		},
	},
	computed: {
		$bench() {
			return getCachedDocumentResource('Bench', this.serverName);
		},
		memoryData() {
			let memory = this.$resources.cadvisor.data?.memory;
			if (!memory) return;

			return {
				datasets: [memory.map((d) => [+new Date(d.date), d.value])],
			};
		},
	},
};
</script>
