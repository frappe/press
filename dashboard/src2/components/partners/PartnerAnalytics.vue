<template>
	<div class="flex flex-col gap-5">
		<DonutChart
			:config="{
				data: [
					{
						product: 'Apple Watch',
						sales: 400,
					},
					{
						product: 'Services',
						sales: 400,
					},
					{
						product: 'iMac',
						sales: 350,
					},
					{
						product: 'Accessories',
						sales: 350,
					},
					{
						product: 'iPad',
						sales: 300,
					},
					{
						product: 'AirPods',
						sales: 300,
					},
					{
						product: 'Apple TV',
						sales: 300,
					},
					{
						product: 'Others',
						sales: 300,
					},
					{
						product: 'Macbook',
						sales: 250,
					},
					{
						product: 'Beats',
						sales: 250,
					},
					{
						product: 'iPhone',
						sales: 200,
					},
					{
						product: 'HomePod',
						sales: 200,
					},
				],
				title: 'Product Sales Distribution',
				subtitle: 'Sales distribution across products',
				categoryColumn: 'product',
				valueColumn: 'sales',
			}"
		/>
	</div>
</template>
<script setup>
import { DonutChart } from 'frappe-ui';
</script>
