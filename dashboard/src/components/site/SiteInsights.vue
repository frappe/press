<template>
	<div
		class="-m-5 flex divide-x"
		:class="{
			'flex-col': $isMobile,
		}"
	>
		<div
			:class="{
				'ml-5 mt-5 w-60 divide-y rounded-sm border': $isMobile,
				'w-60': !$isMobile,
			}"
		>
			<template v-for="tab in tabs">
				<router-link
					:to="{ name: tab.value }"
					class="flex cursor-pointer text-base text-gray-600 hover:bg-gray-100"
					:class="{
						' bg-gray-50 text-gray-800': isActiveTab(tab),
						'text-gray-600': !isActiveTab(tab),
						'border-b': !$isMobile,
					}"
				>
					<div
						class="px-4"
						:class="{
							'py-2': $isMobile,
							'py-2.5': !$isMobile,
						}"
					>
						{{ tab.label }}
					</div>
				</router-link>
			</template>
		</div>
		<div class="w-full overflow-auto sm:h-[88vh]">
			<router-view />
		</div>
	</div>
</template>

<script>
export default {
	name: 'SiteInsights',
	props: ['site'],
	data() {
		return {
			tabs: [
				{
					label: 'Analytics',
					value: 'Site Analytics',
				},
				{
					label: 'Reports',
					value: 'Site Performance Reports',
					children: [
						'Site Performance Slow Queries',
						'Site Performance Binary Logs',
						'Site Performance Process List',
						'Site Performance Request Logs',
						'Site Performance Deadlock Report',
					],
				},
				{
					label: 'Logs',
					value: 'Site Logs',
					children: ['Site Log'],
				},
				{
					label: 'Jobs',
					value: 'Site Jobs',
					children: ['Site Job'],
				},
			],
		};
	},
	mounted() {
		if (this.$route.name === 'Site Insights') {
			this.$router.push({ name: 'Site Analytics' });
		}
	},
	methods: {
		isActiveTab(tab) {
			return [tab.value, ...(tab.children || [])].find(
				(child) => child === this.$route.name,
			);
		},
	},
};
</script>
