<template>
	<div class="flex flex-col gap-5 overflow-y-auto px-10 py-6">
		<div class="grid grid-cols-4 gap-5">
			<NumberChart
				:config="{
					title: 'Current Tier',
					value: partnerDetails.data?.partner_type,
				}"
				class="border rounded-md"
			/>

			<NumberChart
				:config="{
					title: 'Certification',
					value: partnerDetails.data?.custom_number_of_certified_members || 0,
				}"
				class="border rounded-md"
			/>

			<NumberChart
				:config="{
					title: 'PMM Rating',
					value: 4,
				}"
				class="border rounded-md"
			/>

			<NumberChart
				:config="{
					title: 'Contribution',
					value: currentMonthContribution.data || 0,
					prefix: team.doc.currency == 'INR' ? '₹' : '$',
					delta: 10,
					deltaSuffix: '%',
				}"
				class="border rounded-md"
			/>
		</div>
		<div class="border rounded-md">
			<AxisChart
				:config="{
					data: axisConfigData,
					title: 'Partner Revenue Contribution',
					subtitle: 'Data for the last 12 months',
					xAxis: {
						key: 'date',
						type: 'time',
						title: 'Month',
						timeGrain: 'month',
					},
					yAxis: {
						title: 'Amount',
					},
					stacked: true,
					series: [
						{
							name: 'amount',
							type: 'area',
						},
					],
				}"
			/>
		</div>
		<div class="flex justify-between gap-5">
			<div class="flex-1 border rounded-md">
				<DonutChart
					:config="{
						data: sitePlanData,
						title: 'Site Plan Distribution',
						categoryColumn: 'plans',
						valueColumn: 'count',
					}"
				/>
			</div>
			<div class="flex-1 border rounded-md">
				<DonutChart
					:config="{
						data: partnerCustomerData,
						title: 'Partner Team Distribution',
						categoryColumn: 'team',
						valueColumn: 'amount',
					}"
				/>
			</div>
		</div>
	</div>
</template>
<script setup>
import { inject, reactive } from 'vue';
import { createResource, NumberChart, AxisChart, DonutChart } from 'frappe-ui';
const team = inject('team');

const partnerDetails = createResource({
	url: 'press.api.partner.get_partner_details',
	auto: true,
	cache: 'partnerDetails',
	params: {
		partner_email: team.doc.partner_email,
	},
});

const currentMonthContribution = createResource({
	url: 'press.api.partner.get_current_month_partner_contribution',
	auto: true,
	cache: 'currentMonthContribution',
	params: {
		partner_email: team.doc.partner_email,
	},
});

let axisConfigData = reactive([]);
createResource({
	url: 'press.api.partner.get_partner_mrr',
	auto: true,
	cache: 'partnerInvoices',
	params: {
		partner_email: team.doc.partner_email,
	},
	onSuccess: (data) => {
		data.forEach((d) => {
			axisConfigData.push({
				date: d.due_date,
				amount: d.total_amount || 0,
			});
		});
	},
});

let sitePlanData = reactive([]);
createResource({
	url: 'press.api.partner.get_dashboard_stats',
	auto: true,
	cache: 'dashboardStats',
	onSuccess: (data) => {
		data.forEach((d) => {
			sitePlanData.push({
				plans: d.plan,
				count: d.count || 0,
			});
		});
	},
});

let partnerCustomerData = reactive([]);
createResource({
	url: 'press.api.partner.get_partner_contribution_list',
	auto: true,
	cache: 'partnerCustomerDistribution',
	params: {
		partner_email: team.doc.partner_email,
	},
	onSuccess: (data) => {
		data.forEach((d) => {
			partnerCustomerData.push({
				team: d.customer_name,
				amount: d.partner_total || 0,
			});
		});
	},
});
</script>
