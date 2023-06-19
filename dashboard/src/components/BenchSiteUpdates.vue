<template>
	<div class="mt-2 space-y-2 divide-y">
		<SiteUpdateCard
			v-for="site in sites"
			:key="site"
			@click.native.self="toggleSite(site)"
			:site="site"
			:selected="selectedSites.includes(site)"
			:selectable="true"
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
		this.selectedSites = this.sites;
		this.$emit('update:selectedSites', this.selectedSites);
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
	},
	watch: {
		selectedSites: {
			handler(sites) {
				// Hardcoded for now, need a better way
				// to manage such dependencies (#TODO)
				// If updating ERPNext, must update Frappe with it

				let frappeUpdateAvailable =
					this.sites.filter(app => app.update_available && app.app == 'frappe')
						.length !== 0;

				if (
					sites.includes('erpnext') &&
					!sites.includes('frappe') &&
					frappeUpdateAvailable
				) {
					sites.push('frappe');
				}
			},
			deep: true,
			immediate: true
		}
	}
};
</script>
