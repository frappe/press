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
			<div class="flex gap-8 items-start flex-col md:flex-row">
				<div class="border rounded-md p-2 h-[8rem] w-[16rem]">
					<NumberChart
						:config="{
							title: 'Month-To-Date Cost',
							value: forecastData?.current_month_to_date_cost,
							prefix: currencySymbol,
							delta: forecastData?.mtd_change,
							deltaSuffix: '% MTD',
						}"
					/>
				</div>
				<div class="border rounded-md p-2 h-[8rem] w-[16rem]">
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
			</div>
			<!-- Charts Section -->
			<div>
				<div
					v-if="axisChartConfig?.data?.length || donutConfig?.data?.length"
					class="grid grid-cols-1 gap-6 lg:grid-cols-2"
				>
					<!-- Stacked Bar Chart for last month, mtd, and forecasted month end -->
					<div class="rounded-md border" v-if="axisChartConfig?.data?.length">
						<AxisChart :config="axisChartConfig" />
					</div>
					<!-- Donut Chart for current month's usage -->
					<div class="rounded-md border" v-if="donutConfig?.data?.length">
						<DonutChart :config="donutConfig" />
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
			const forecastDataValue = forecastData.value;
			if (
				!forecastDataValue.last_month_cost &&
				!forecastDataValue.forecasted_month_end &&
				!forecastDataValue.current_month_to_date_cost
			) {
				return {};
			}

			// Month Labels
			const now = new Date();
			const formatter = new Intl.DateTimeFormat('en-US', {
				month: 'long',
				year: 'numeric',
			});
			const currentMonthName = formatter.format(now);
			const lastMonthName = formatter.format(
				new Date(now.getFullYear(), now.getMonth() - 1, 1),
			);

			const {
				last_month_usage_breakdown = {},
				month_to_date_usage_breakdown = {},
				forecasted_usage_breakdown = {},
			} = forecastDataValue.usage_breakdown;

			const data = [
				{
					period: `Last Month\n(${lastMonthName})`,
					...last_month_usage_breakdown,
				},
				{
					period: `Month To Date\n(${currentMonthName})`,
					...month_to_date_usage_breakdown,
				},
				{
					period: `Forecast\n(${currentMonthName})`,
					...forecasted_usage_breakdown,
				},
			];

			// set of unique services from all breakdowns
			const uniqueServices = new Set([
				...Object.keys(last_month_usage_breakdown),
				...Object.keys(month_to_date_usage_breakdown),
				...Object.keys(forecasted_usage_breakdown),
			]);

			const series = Array.from(uniqueServices, (service) => ({
				name: service,
				type: 'bar',
			}));

			return {
				title: 'Billing Comparison',
				data,
				stacked: true,
				xAxis: {
					key: 'period',
					title: 'Time Period',
					type: 'category',
				},
				yAxis: {
					title: `Amount (${currencySymbol.value})`,
				},
				series,
			};
		});

		const donutConfig = computed(() => {
			const data = [];
			let usage_breakdown =
				forecastData.value?.usage_breakdown?.month_to_date_usage_breakdown ||
				{};
			for (let key in usage_breakdown) {
				data.push({ service: key, amount: usage_breakdown[key] });
			}
			return {
				data,
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
