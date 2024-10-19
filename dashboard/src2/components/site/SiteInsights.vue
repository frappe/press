<template>
	<div class="-m-5 flex divide-x">
		<div class="h-screen w-full overflow-auto pt-5">
			<router-view />
		</div>
		<div class="w-60 divide-y">
			<template v-for="tab in tabs">
				<router-link
					:to="{ name: tab.value }"
					v
					class="flex cursor-pointer text-base text-gray-600 hover:bg-gray-100"
					:class="{
						' bg-gray-50 text-gray-800': [
							tab.value,
							...(tab.children || [])
						].find(child => child === $route.name),
						'text-gray-600': ![tab.value, ...(tab.children || [])].find(
							child => child === $route.name
						)
					}"
				>
					<div class="px-4 py-2">
						{{ tab.label }}
					</div>
				</router-link>
			</template>
		</div>
	</div>
</template>

<script>
import LineChart from '@/components/charts/LineChart.vue';

export default {
	name: 'SiteInsights',
	props: ['site'],
	components: {
		LineChart
	},
	data() {
		return {
			tabs: [
				{
					label: 'Analytics',
					value: 'Site Analytics'
				},
				{
					label: 'Reports',
					value: 'Site Performance Reports',
					children: [
						'Site Performance Slow Queries',
						'Site Performance Binary Logs',
						'Site Performance Process List',
						'Site Performance Request Logs',
						'Site Performance Deadlock Report'
					]
				},
				{
					label: 'Logs',
					value: 'Site Logs',
					children: ['Site Log']
				},
				{
					label: 'Jobs',
					value: 'Site Jobs',
					children: ['Site Job']
				}
			]
		};
	},
	mounted() {
		if (this.$route.name === 'Site Insights') {
			this.$router.push({ name: 'Site Analytics' });
		}
	}
};
</script>
