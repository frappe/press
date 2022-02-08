<template>
	<div class="mt-2 space-y-2 divide-y">
		<AppUpdateCard
			v-for="app in appsWithUpdates"
			:key="app.app"
			@click.native.self="toggleApp(app)"
			:app="app"
			:selected="selectedApps.includes(app.app)"
			:uninstall="false"
			:selectable="true"
		/>
		<AppUpdateCard
			v-for="app in removedApps"
			:key="app.name"
			@click.native="toggleApp(app)"
			:app="app"
			:selected="selectedApps.includes(app.app)"
			:uninstall="true"
		/>
	</div>
</template>
<script>
import AppUpdateCard from './AppUpdateCard.vue';

export default {
	name: 'BenchAppUpdates',
	props: ['apps', 'removedApps'],
	components: {
		AppUpdateCard
	},
	data() {
		return {
			selectedApps: []
		};
	},
	mounted() {
		// Select all apps by default
		this.selectedApps = this.appsWithUpdates.map(app => app.app);
		this.$emit('update:selectedApps', this.selectedApps);
	},
	methods: {
		toggleApp(app) {
			if (!this.selectedApps.includes(app.app)) {
				this.selectedApps.push(app.app);
				this.$emit('update:selectedApps', this.selectedApps);
			} else {
				this.selectedApps = this.selectedApps.filter(a => a !== app.app);
				this.$emit('update:selectedApps', this.selectedApps);
			}
		}
	},
	computed: {
		appsWithUpdates() {
			return this.apps.filter(app => app.update_available);
		}
	},
	watch: {
		selectedApps(apps) {
			// Hardcoded for now, need a better way
			// to manage such dependencies (#TODO)
			// If updating ERPNext, must update Frappe with it

			let frappeUpdateAvailable =
				this.apps.filter(app => app.update_available && app.app == 'frappe')
					.length !== 0;

			if (
				apps.includes('erpnext') &&
				!apps.includes('frappe') &&
				frappeUpdateAvailable
			) {
				apps.push('frappe');
			}
		}
	}
};
</script>
