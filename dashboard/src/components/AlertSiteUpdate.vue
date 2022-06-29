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
			<SiteAppUpdates :apps="updateInformation.apps" />
			<div class="mt-4">
				<!-- Skip Failing Checkbox -->
				<input
					id="skip-failing"
					type="checkbox"
					class="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
					v-model="wantToSkipFailingPatches"
				/>
				<label for="skip-failing" class="ml-1 text-sm text-gray-900">
					Skip failing patches?
				</label>
			</div>
			<ErrorMessage class="mt-1" :error="$resources.scheduleUpdate.error" />
			<template #actions>
				<Button
					type="primary"
					@click="$resources.scheduleUpdate.fetch()"
					:loading="$resources.scheduleUpdate.loading"
				>
					Update now
				</Button>
			</template>
		</Dialog>
	</Alert>
</template>
<script>
import SiteAppUpdates from './SiteAppUpdates.vue';
export default {
	name: 'AlertSiteUpdate',
	props: ['site'],
	components: {
		SiteAppUpdates
	},
	data() {
		return {
			showUpdatesDialog: false,
			wantToSkipFailingPatches: false
		};
	},
	resources: {
		updateInformation() {
			return {
				method: 'press.api.site.check_for_updates',
				params: {
					name: this.site?.name
				},
				auto: true
			};
		},
		lastMigrateFailed() {
			return {
				method: 'press.api.site.last_migrate_failed',
				params: {
					name: this.site?.name
				},
				auto: true
			};
		},
		scheduleUpdate() {
			return {
				method: 'press.api.site.update',
				params: {
					name: this.site?.name,
					skip_failing_patches: this.wantToSkipFailingPatches
				},
				onSuccess() {
					this.showUpdatesDialog = false;
					this.$notify({
						title: 'Site update scheduled successfully!',
						icon: 'check',
						color: 'green'
					});
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
		},
		lastMigrateFailed() {
			return this.$resources.lastMigrateFailed.data;
		}
	}
};
</script>
