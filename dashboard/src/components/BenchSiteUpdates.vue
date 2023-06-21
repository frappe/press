<template>
	<div class="mt-2 space-y-2 divide-y max-h-96 overflow-auto">
		<SiteUpdateCard
			v-for="site in sites"
			:key="site.name"
			@click.native.self="toggleSite(site)"
			:site="site.name"
			:selected="selectedSites.map(s => s.name).includes(site.name)"
			:selectable="true"
			v-model:selectedSites="selectedSites"
		/>
	</div>
</template>
<script>
import SiteUpdateCard from './SiteUpdateCard.vue';

export default {
	name: 'BenchSiteUpdates',
	props: ['sites'],
	components: {
		SiteUpdateCard
	},
	data() {
		return {
			selectedSites: []
		};
	},
	mounted() {
		// Select all sites by default
		this.$emit('update:selectedSites', []);
	},
	methods: {
		toggleSite(site) {
			if (!this.selectedSites.includes(site)) {
				this.selectedSites.push(site);
				this.$emit('update:selectedSites', this.selectedSites);
			} else {
				this.selectedSites = this.selectedSites.filter(a => a !== site);
				this.$emit('update:selectedSites', this.selectedSites);
			}
		}
	}
};
</script>
