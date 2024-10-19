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
						' bg-gray-50 text-gray-800': $route.name === tab.value,
						'text-gray-600': $route.name !== tab.value
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
					value: 'Site Performance Reports'
				},
				{
					label: 'Logs',
					value: 'Site Logs'
				},
				{
					label: 'Jobs',
					value: 'Site Jobs'
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
