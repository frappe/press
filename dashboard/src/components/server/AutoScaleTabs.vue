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
			<template v-for="tab in tabs" :key="tab.value">
				<router-link
					:to="{
						name: tab.value,
						query: {
							secondaryServer: secondaryServer,
						},
					}"
					class="flex cursor-pointer text-base hover:bg-gray-100"
					:class="{
						'bg-gray-50 text-gray-800': isActiveTab(tab),
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
	name: 'AutoScaleTabs',
	props: ['server', 'secondaryServer'],
	data() {
		return {
			tabs: [
				{ label: 'Triggered', value: 'Triggered' },
				{ label: 'Scheduled', value: 'Scheduled' },
			],
		};
	},
	mounted() {
		// If query params are missing, add them
		if (!this.$route.query.secondaryServer) {
			this.$router.replace({
				query: {
					secondaryServer: this.secondaryServer,
				},
			});
		}
	},
	methods: {
		isActiveTab(tab) {
			return tab.value === this.$route.name;
		},
	},
};
</script>
