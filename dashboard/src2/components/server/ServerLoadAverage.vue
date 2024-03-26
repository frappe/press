<template>
	<div class="rounded-md border">
		<div class="flex h-12 items-center justify-between border-b px-5">
			<h2 class="text-lg font-medium text-gray-900">Load Average</h2>
			<div class="flex items-center space-x-2">
				<Button
					icon="help-circle"
					variant="ghost"
					:link="'https://frappecloud.com/docs/server-analytics#load-average'"
				/>
				<router-link
					class="text-base text-gray-600 hover:text-gray-700"
					:to="{ name: 'Server Detail Analytics', params: { name: server } }"
				>
					All analytics →
				</router-link>
			</div>
		</div>
		<LineChart
			class="h-52 p-2"
			type="time"
			title="Load Average"
			:key="loadAverageData"
			:chartTheme="[
				$theme.colors.green[500],
				$theme.colors.yellow[400],
				$theme.colors.red[500]
			]"
			:data="loadAverageData"
			:showCard="false"
			:loading="$resources.loadavg.loading"
			:error="$resources.loadavg.error"
		/>
	</div>
</template>
<script>
import dayjs from '../../utils/dayjs';
import LineChart from '@/components/charts/LineChart.vue';

export default {
	name: 'CPUUsage',
	props: ['server'],
	components: { LineChart },
	resources: {
		loadavg() {
			let localTimezone = dayjs.tz.guess();
			return {
				url: 'press.api.server.analytics',
				params: {
					name: this.server,
					timezone: localTimezone,
					query: 'loadavg',
					duration: '6 Hour'
				},
				auto: true
			};
		}
	},
	computed: {
		loadAverageData() {
			let loadavg = this.$resources.loadavg.data;
			if (!loadavg) return;

			loadavg.datasets.sort(
				(a, b) => Number(a.name.split(' ')[2]) - Number(b.name.split(' ')[2])
			);

			return this.transformMultiLineChartData(loadavg);
		}
	},
	methods: {
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
