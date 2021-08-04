<template>
	<Card title="Site info" subtitle="General information about your site">
		<div class="divide-y">
			<div class="flex items-center py-3">
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
			<PressUIAction
				name="Toggle Site Activate"
				v-if="['Active', 'Inactive'].includes(site.status)"
				v-slot="{ action, execute }"
			>
				<ListItem
					:title="site.status == 'Active' ? 'Deactivate Site' : 'Activate Site'"
					:description="
						site.status == 'Active'
							? 'When you deactivate your site, you cannot access it'
							: 'When you activate your site, you can access it'
					"
				>
					<template slot="actions">
						<Button @click="onToggleActivate(execute)">
							{{ site.status == 'Active' ? 'Deactivate' : 'Activate' }}
						</Button>
					</template>
				</ListItem>
			</PressUIAction>
		</div>
	</Card>
</template>
<script>
import SiteDrop from './SiteDrop.vue';
export default {
	name: 'SiteOverviewInfo',
	props: ['site', 'info'],
	components: {
		SiteDrop
	},
	methods: {
		onToggleActivate(execute) {
			let siteActive = this.site.status == 'Active';
			let activate = {
				title: 'Activate Site',
				message: 'Are you sure you want to activate this site?',
				actionLabel: 'Activate',
				actionType: 'primary'
			};
			let deactivate = {
				title: 'Deactivate Site',
				message: `
					Are you sure you want to deactivate this site? The site will go in an inactive state.
					It won't be accessible and background jobs won't run. You will still be charged for it.
				`,
				actionLabel: 'Deactivate',
				actionType: 'danger'
			};
			this.$confirm({
				...(siteActive ? deactivate : activate),
				resource: execute,
				action: () => {
					execute
						.submit({
							name: 'Toggle Site Activate',
							site: this.site.name,
							activate: siteActive ? false : true
						})
						.then(() => {
							setTimeout(() => window.location.reload(), 1000);
						});
				}
			});
		}
	}
};
</script>
