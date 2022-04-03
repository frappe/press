<template>
	<div>
		<Section title="Apps" :description="'Apps installed on your bench'">
			<SectionCard>
				<div
					class="items-center px-6 py-3 hover:bg-gray-50"
					v-for="app in apps"
					:key="app.app"
				>
					<div class="text-base font-semibold text-brand">
						{{ app.title }}
					</div>

					<p class="text-sm text-gray-800">
						{{ app.repository_owner }}:{{ app.branch }}
					</p>
				</div>
			</SectionCard>
			<Button
				class="mt-6"
				type="primary"
				:route="'/benches/' + this.bench.name + '/apps/new'"
			>
				Add App
			</Button>
		</Section>
	</div>
</template>

<script>
export default {
	name: 'BenchApps',
	props: ['bench'],
	resources: {
		apps() {
			return {
				method: 'press.api.bench.apps',
				params: {
					name: this.bench?.name
				},
				auto: true
			};
		}
	},
	computed: {
		apps() {
			return this.$resources.apps.data;
		}
	}
};
</script>
