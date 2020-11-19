<template>
	<div>
		<Section title="Apps" :description="'Apps installed on your bench'">
			<SectionCard>
				<div
					class="px-6 py-3 hover:bg-gray-50 items-center"
					v-for="application in applications"
					:key="application.application"
				>
					<div class="font-semibold text-brand text-base">
						{{ application.title }}
					</div>

					<p class="text-sm text-gray-800">
						{{ application.repository_owner }}:{{ application.branch }}
					</p>
				</div>
			</SectionCard>
		</Section>
	</div>
</template>

<script>
export default {
	name: 'BenchApps',
	props: ['bench'],
	resources: {
		applications() {
			return {
				method: 'press.api.bench.applications',
				params: {
					name: this.bench.name
				},
				auto: true
			};
		}
	},
	computed: {
		applications() {
			return this.$resources.applications.data;
		}
	}
};
</script>
