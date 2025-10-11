<template>
	<div class="flex flex-1 flex-col gap-8 overflow-y-auto px-10 md:px-20 pt-10">
		<div
			v-if="$resources.forecastData.loading"
			class="flex justify-center py-12"
		>
			<LoadingIndicator class="h-8 w-8" />
		</div>

		<div v-else-if="$resources.forecastData.error" class="py-12">
			<ErrorMessage :message="$resources.forecastData.error" />
		</div>

		<div v-else-if="forecastData" class="space-y-8">
			<div class="flex gap-2 items-start border">
				<NumberChart
					:config="{
						title: 'Month-To-Date Cost',
						value: forecastData?.current_month_to_date_cost,
						prefix: currencySymbol,
						delta: forecastData?.mtd_change,
						deltaSuffix: '% MTD',
					}"
				/>
				<NumberChart
					:config="{
						title: 'Forecasted Month End Cost',
						value: forecastData?.forecasted_month_end,
						prefix: currencySymbol,
						delta: forecastData?.month_over_month_change,
						deltaSuffix: '% MoM',
					}"
				/>
			</div>
			<!-- Charts Section -->
			<div>
				<div
					v-if="
						forecastData.last_month_cost ||
						forecastData.current_month_to_date_cost
					"
					class="grid grid-cols-1 gap-6 md:grid-cols-2"
				>
					<!-- Bar Chart -->
					<div class="border">
						<AxisChart :config="axisChartConfig" />
					</div>
					<!-- Pie Chart -->
					<div class="border">
						<div v-if="forecastData?.usage_breakdown?.length > 0">
							<DonutChart :config="donutConfig" />
						</div>
					</div>
				</div>
				<div v-else class="flex h-64 items-center justify-center text-gray-500">
					No usage data available for this month
				</div>
			</div>
		</div>
	</div>
</template>

<script>
import {
	LoadingIndicator,
	ErrorMessage,
	createResource,
	AxisChart,
	DonutChart,
	NumberChart,
} from 'frappe-ui';
import { inject, computed } from 'vue';

export default {
	name: 'BillingForecast',
	components: {
		LoadingIndicator,
		ErrorMessage,
		AxisChart,
		DonutChart,
		NumberChart,
	},
	setup() {
		const team = inject('team');

		const forecastResource = createResource({
			url: 'press.api.billing.billing_forecast',
			cache: 'forecastResource',
			auto: true,
		});

		const forecastData = computed(() => {
			return forecastResource.data;
		});

		const currencySymbol = computed(() => {
			return team.doc?.currency === 'INR' ? '₹' : '$';
		});

		const axisChartConfig = computed(() => {
			const lastMonthCost = forecastData.value.last_month_cost || 0;
			const currentMonthCost =
				forecastData.value.current_month_to_date_cost || 0;
			const forecastedCost = forecastData.value.forecasted_month_end || 0;

			if (!lastMonthCost && !currentMonthCost && !forecastedCost) {
				return {};
			}

			// Get current date for proper label
			const now = new Date();
			const lastMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1);
			const currentMonth = new Date(now.getFullYear(), now.getMonth(), 1);

			// Format month names
			const lastMonthName = lastMonth.toLocaleDateString('en-US', {
				month: 'long',
				year: 'numeric',
			});
			const currentMonthName = currentMonth.toLocaleDateString('en-US', {
				month: 'long',
				year: 'numeric',
			});

			const currency = team.doc?.currency === 'INR' ? '₹' : '$';

			const data = [
				{
					period: `Last Month\n(${lastMonthName})`,
					amount: Number(lastMonthCost),
				},
				{
					period: `Month To Date\n(${currentMonthName})`,
					amount: Number(currentMonthCost),
				},
				{
					period: `Forecast\n(${currentMonthName})`,
					amount: Number(forecastedCost),
				},
			];

			return {
				data: data,
				title: 'Billing Comparison',
				xAxis: {
					key: 'period',
					title: 'Time Period',
					type: 'category',
				},
				yAxis: {
					title: `Amount (${currency})`,
				},
				series: [
					{
						name: 'amount',
						type: 'bar',
					},
				],
			};
		});

		const donutConfig = computed(() => {
			return {
				data: [...forecastData.value.usage_breakdown] || [],
				title: 'Month-To-Date Cost Breakdown',
				categoryColumn: 'service',
				valueColumn: 'amount',
			};
		});

		return {
			$resources: {
				forecastData: forecastResource,
			},
			team,
			currencySymbol,
			forecastData,
			axisChartConfig,
			donutConfig,
		};
	},
};
</script>
