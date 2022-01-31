<template>
	<Card title="Site info" subtitle="General information about your site">
		<div class="divide-y">
			<div class="flex items-center py-3">
				<Avatar
					v-if="info.owner"
					:imageURL="info.owner.user_image"
					:label="info.owner.first_name"
				/>
				<div class="flex items-center justify-between flex-1 ml-3">
					<div>
						<div class="text-base text-gray-600">Owned By</div>
						<div class="text-base font-medium text-gray-900">
							{{ info.owner.first_name }}
							{{ info.owner.last_name }}
						</div>
					</div>
					<div class="text-right">
						<div class="text-base text-gray-600">Created On</div>
						<div class="text-base font-medium text-gray-900">
							{{ formatDate(info.created_on, 'DATE_FULL') }}
						</div>
					</div>
					<div v-if="info.last_deployed" class="text-right">
						<div class="text-base text-gray-600">
							Last Deployed
						</div>

						<div class="text-base font-medium text-gray-900">
							{{
								$date(info.last_deployed).toLocaleString({
									month: 'long',
									day: 'numeric'
								})
							}}
						</div>
					</div>
				</div>
			</div>

			<ListItem
				v-if="site.group && site.status !== 'Pending'"
				title="Auto Update Site"
				description="Automatically schedule site updates whenever available"
			>
				<template slot="actions">
					<LoadingIndicator v-if="loading" />
					<input
						v-show="!loading"
						id="auto-update-checkbox"
						@input="changeAutoUpdateSettings"
						type="checkbox"
						class="
							h-4
							w-4
							text-blue-600
							focus:ring-blue-500
							border-gray-300
							rounded
							mr-1
						"
					/>
				</template>
			</ListItem>
			<ListItem
				v-if="site.status == 'Active'"
				title="Deactivate Site"
				description="The site will go inactive and won't be publicly accessible"
			>
				<Button slot="actions" @click="onDeactivateClick" class="flex-shrink-0">
					Deactivate Site
				</Button>
			</ListItem>

			<ListItem
				v-if="site.status == 'Inactive'"
				title="Activate Site"
				description="The site will become active and will be accessible"
			>
				<Button slot="actions" @click="onActivateClick" class="flex-shrink-0">
					Activate Site
				</Button>
			</ListItem>

			<ListItem
				v-if="site.status !== 'Pending'"
				title="Drop Site"
				description="Once you drop site your site, there is no going back"
			>
				<template slot="actions">
					<SiteDrop :site="site" v-slot="{ showDialog }">
						<Button @click="showDialog">
							<span class="text-red-600">Drop Site</span>
						</Button>
					</SiteDrop>
				</template>
			</ListItem>
		</div>
	</Card>
</template>
<script>
import SiteDrop from './SiteDrop.vue';
export default {
	name: 'SiteOverviewInfo',
	props: ['site', 'info'],
	components: { SiteDrop },
	data() {
		return {
			loading: false
		};
	},
	mounted() {
		const autoUpdateCheckbox = document.getElementById('auto-update-checkbox');

		if (autoUpdateCheckbox) {
			autoUpdateCheckbox.checked = this.info.auto_updates_enabled;
		}
	},
	methods: {
		changeAutoUpdateSettings(event) {
			event.preventDefault();
			this.loading = true;

			return this.$call('press.api.site.change_auto_update', {
				name: this.site.name,
				auto_update_enabled: event.target.checked
			}).then(() => {
				setTimeout(() => window.location.reload(), 1000);
			});
		},
		onDeactivateClick() {
			this.$confirm({
				title: 'Deactivate Site',
				message: `
					Are you sure you want to deactivate this site? The site will go in an inactive state.
					It won't be accessible and background jobs won't run. You will <strong>still be charged</strong> for it.
				`,
				actionLabel: 'Deactivate',
				actionType: 'danger',
				action: () => this.deactivate()
			});
		},
		onActivateClick() {
			this.$confirm({
				title: 'Activate Site',
				message: 'Are you sure you want to activate this site?',
				actionLabel: 'Activate',
				actionType: 'primary',
				action: () => this.activate()
			});
		},
		deactivate() {
			return this.$call('press.api.site.deactivate', {
				name: this.site.name
			}).then(() => {
				setTimeout(() => window.location.reload(), 1000);
			});
		},
		activate() {
			this.$call('press.api.site.activate', {
				name: this.site.name
			});
			this.$notify({
				title: 'Site activated successfully!',
				message: 'You can now access your site',
				icon: 'check',
				color: 'green'
			});
			setTimeout(() => window.location.reload(), 1000);
		}
	}
};
</script>
