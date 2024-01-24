<template>
	<div class="rounded-md border">
		<div class="flex h-12 items-center justify-between border-b px-5">
			<h2 class="text-lg font-medium text-gray-900">Daily Usage</h2>
			<router-link
				class="text-base text-gray-600 hover:text-gray-700"
				:to="`/sites/${site.name}/analytics`"
			>
				All analytics →
			</router-link>
		</div>
		<LineChart
			type="time"
			:key="dailyUsageData"
			:data="dailyUsageData"
			unit="seconds"
			:chartTheme="[$theme.colors.purple[500]]"
			:loading="$resources.requestCounter.loading"
			:error="$resources.requestCounter.error"
			:showCard="false"
			class="h-52 p-2"
		>
			<template #actions>
				<router-link
					class="text-base text-gray-600 hover:text-gray-700"
					:to="`/sites/${site.name}/analytics`"
				>
					All analytics →
				</router-link>
			</template>
		</LineChart>
	</div>
</template>
<script>
import { DateTime } from 'luxon';
import LineChart from '@/components/charts/LineChart.vue';

export default {
	name: 'CPUUsage',
	props: ['site'],
	components: { LineChart },
	resources: {
		requestCounter() {
			let localTimezone = DateTime.local().zoneName;
			return {
				url: 'press.api.analytics.daily_usage',
				params: { name: this.site?.name, timezone: localTimezone },
				auto: true
			};
		}
	},
	computed: {
		dailyUsageData() {
			let dailyUsageData = this.$resources.requestCounter.data?.data;
			if (!dailyUsageData) return;
			let plan_limit = this.$resources.requestCounter.data.plan_limit;

			return {
				datasets: [
					dailyUsageData.map(d => [+new Date(d.date), d.value / 1000000])
				],
				// daily limit marker
				markLine: {
					data: [
						{
							name: 'Daily Compute Limit',
							yAxis: plan_limit,
							label: {
								formatter: '{b}: {c} seconds',
								position: 'middle'
							},
							lineStyle: {
								color: '#f5222d'
							}
						}
					],
					symbol: ['none', 'none']
				}
			};
		}
	}
};
</script>
