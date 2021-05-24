<template>
	<Alert title="Update Available" v-if="show">
		<span>
			A new update is available for your site. Would you like to update your
			site now?
		</span>
		<template #actions>
			<Button type="primary" @click="showUpdatesDialog = true">
				Show updates
			</Button>
		</template>
		<Dialog title="Updates available" v-model="showUpdatesDialog">
			<AppUpdates :apps="updateInformation.apps" />
			<template #actions>
				<Button
					type="primary"
					@click="$resources.scheduleUpdate.fetch()"
					:loading="$resources.scheduleUpdate.loading"
				>
					Schedule update
				</Button>
			</template>
		</Dialog>
	</Alert>
</template>
<script>
import AppUpdates from './AppUpdates.vue';
export default {
	name: 'AlertSiteUpdate',
	props: ['site'],
	components: {
		AppUpdates
	},
	data() {
		return {
			showUpdatesDialog: false
		};
	},
	resources: {
		updateInformation() {
			return {
				method: 'press.api.site.check_for_updates',
				params: {
					name: this.site.name
				},
				auto: true
			};
		},
		scheduleUpdate() {
			return {
				method: 'press.api.site.update',
				params: {
					name: this.site.name
				}
			};
		}
	},
	computed: {
		show() {
			if (this.updateInformation) {
				return (
					this.updateInformation.update_available &&
					['Active', 'Inactive', 'Suspended'].includes(this.site.status)
				);
			}
		},
		updateInformation() {
			return this.$resources.updateInformation.data;
		}
	}
};
</script>
