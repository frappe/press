<template>
	<div class="grid grid-cols-2 gap-6">
		<div class="min-h-[240px] rounded-lg border p-4">
			<div class="flex items-center justify-between">
				<div class="text-xl font-semibold">Sites</div>
				<Button variant="ghost" :route="{ name: 'Site List' }">
					View all
				</Button>
			</div>
			<div class="mt-4">
				<router-link
					class="flex items-center justify-between rounded border-b px-2 py-2 hover:bg-gray-50"
					v-for="site in sites"
					:key="site.name"
					:to="{ name: 'Site Detail', params: { name: site.name } }"
				>
					<div class="text-base text-gray-900">
						{{ site.host_name || site.name }}
					</div>
					<div>
						<Badge :label="site.status" />
					</div>
				</router-link>
			</div>
		</div>
		<div class="rounded-lg border p-4">
			<div class="text-xl font-semibold">Benches</div>
		</div>
	</div>
</template>
<script>
export default {
	name: 'HomeSummary',
	resources: {
		home() {
			if (!this.$team.doc?.name) return;
			return {
				url: 'press.api.client.run_doc_method',
				cache: ['home_data', this.$team.doc.name],
				makeParams() {
					return {
						dt: 'Team',
						dn: this.$team.doc.name,
						method: 'get_home_data'
					};
				},
				auto: true
			};
		}
	},
	computed: {
		sites() {
			return this.$resources.home.data?.message.sites || [];
		}
	}
};
</script>
