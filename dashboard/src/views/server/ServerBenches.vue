<template>
	<ListView :items="benches" :dropdownItems="dropdownItems" />
</template>
<script>
import ListView from '@/components/ListView.vue';
export default {
	name: 'ServerBenches',
	components: { ListView },
	props: ['server'],
	resources: {
		benches() {
			return {
				method: 'press.api.server.groups',
				params: {
					name: this.server?.name
				},
				auto: true
			};
		}
	},
	computed: {
		benches() {
			if (!this.$resources.benches.data) {
				return [];
			}

			return this.$resources.benches.data.map(bench => ({
				name: bench.title,
				status: bench.status,
				version: bench.version,
				number_of_sites: bench.number_of_sites,
				number_of_apps: bench.number_of_apps,
				link: { name: 'BenchOverview', params: { benchName: bench.name } }
			}));
		}
	},
	methods: {
		dropdownItems(bench) {
			return [
				{
					label: 'New Site',
					onClick: () => {
						this.$router.push(`/${bench.name}/new`);
					}
				},
				{
					label: 'View Versions',
					onClick: () => {
						this.$router.push(`/benches/${bench.name}/versions`);
					}
				}
			];
		}
	}
};
</script>
