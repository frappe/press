<template>
	<div class="home">
		<PageHeader>
			<h1 slot="title">Dashboard</h1>
		</PageHeader>
		<div class="px-4 sm:px-8">
			<div class="flex">
				<div class="w-1/2 p-8" v-if="sites">
					<div class="font-medium">Sites</div>
					<div
						v-for="site in sites"
						:key="site.status"
						class="mt-5 flex items-center justify-between text-sm"
					>
						<div>{{ site.status }}</div>
						<div>{{ site.count }}</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
export default {
	name: 'Home',
	data() {
		return {
			sites: null,
			plans: null
		};
	},
	mounted() {
		// TODO: Remove this line when ready
		this.redirectToSites();
		this.fetchAll();
	},
	methods: {
		async redirectToSites() {
			this.$router.push('/sites');
		},
		async fetchAll() {
			let result = await this.$call('press.api.dashboard.all');
			this.sites = result.sites;
			this.plans = result.plans;
			if (this.sites.length === 0) {
				this.redirectToSites();
			}
		}
	}
};
</script>
