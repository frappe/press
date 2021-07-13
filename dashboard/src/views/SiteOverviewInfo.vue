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
	}
};
</script>
