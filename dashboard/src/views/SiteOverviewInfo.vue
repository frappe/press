<template>
	<Card title="Site info" subtitle="General information about your site">
		<div class="divide-y">
			<div class="flex items-center py-2">
				<Avatar
					v-if="info.created_by"
					:imageURL="info.created_by.user_image"
					:label="info.created_by.first_name"
				/>
				<div class="flex items-center justify-between flex-1 ml-3">
					<div>
						<div class="text-base text-gray-600">Created By</div>
						<div class="text-base font-medium text-gray-900">
							{{ info.created_by.first_name }}
							{{ info.created_by.last_name }}
						</div>
					</div>
					<div class="text-right">
						<div class="text-base text-gray-600">Created On</div>
						<div class="text-base font-medium text-gray-900">
							{{
								$date(info.created_on).toLocaleString({
									month: 'long',
									day: 'numeric'
								})
							}}
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
			<div class="flex items-center justify-between py-2">
				<template v-if="site.status == 'Active'">
					<div>
						<div class="text-base font-medium text-gray-900">
							Deactivate Site
						</div>
						<div class="mt-1 text-base text-gray-600">
							The site will go inactive and billing will be paused
						</div>
					</div>
					<Button @click="onDeactivateClick" class="flex-shrink-0">
						Deactivate Site
					</Button>
				</template>
				<template v-if="site.status == 'Inactive'">
					<div>
						<div class="text-base font-medium text-gray-900">
							Activate Site
						</div>
						<div class="mt-1 text-base text-gray-600">
							The site will become active again and billing will resume
						</div>
					</div>
					<Button @click="onActivateClick" class="flex-shrink-0">
						Activate Site
					</Button>
				</template>
			</div>
			<div
				v-if="site.status !== 'Pending'"
				class="flex items-center justify-between py-2"
			>
				<div>
					<div class="text-base font-medium text-gray-900">
						Drop Site
					</div>
					<div class="mt-1 text-base text-gray-600">
						Once you drop site your site, there is no going back
					</div>
				</div>
				<SiteDrop :site="site" v-slot="{ showDialog }">
					<Button @click="showDialog">
						<span class="text-red-600">Drop Site</span>
					</Button>
				</SiteDrop>
			</div>
		</div>
	</Card>
</template>
<script>
import SiteDrop from './SiteDrop.vue';
export default {
	name: 'SiteOverviewInfo',
	props: ['site', 'info'],
	components: { SiteDrop },
	methods: {
		onDeactivateClick() {
			this.$confirm({
				title: 'Deactivate Site',
				message:
					"Are you sure you want to deactivate this site? The site will go in an inactive state. It won't be accessible and background jobs won't run. We will also not charge you for it.",
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
