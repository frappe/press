<template>
	<div class="flex space-x-6 divide-x">
		<div
			class="h-min w-60 divide-y overflow-hidden rounded-sm border border-gray-200"
		>
			<template v-for="tab in tabs">
				<router-link
					:to="{ name: tab.value }"
					v
					class="flex cursor-pointer text-base text-gray-600 hover:bg-gray-50"
					:class="{
						' text-gray-800': currentTab === tab.value,
						'text-gray-600': currentTab !== tab.value
					}"
					@click="currentTab = tab.value"
				>
					<div
						v-if="currentTab === tab.value"
						class="inline w-0.5 bg-gray-800"
					></div>
					<div
						class="px-4 py-2"
						:class="{
							'-ml-0.5': currentTab === tab.value
						}"
					>
						{{ tab.label }}
					</div>
				</router-link>
			</template>
		</div>
		<div class="min-h-screen w-full">
			<router-view />
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
					label: 'Performance Reports',
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
			],
			currentTab: this.$route.name
		};
	},
	mounted() {
		if (this.$route.name === 'Site Insights') {
			this.$router.push({ name: 'Site Analytics' });
		}
	}
};
</script>
