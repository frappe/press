<template>
	<Alert title="Update Available" v-if="show">
		<span>
			A new update is available for your site. Would you like to update your
			site now?
		</span>
		<template #actions>
			<Button
				type="primary"
				@click="$resources.scheduleUpdate.fetch()"
				:disabled="$resources.scheduleUpdate.loading"
			>
				Update
			</Button>
		</template>
	</Alert>
</template>
<script>
export default {
	name: 'AlertSiteUpdate',
	props: ['site'],
	resources: {
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
			return (
				this.site.update_available &&
				(this.site.status === 'Active' ||
					this.site.status === 'Inactive' ||
					this.site.status === 'Suspended')
			);
		}
	}
};
</script>
