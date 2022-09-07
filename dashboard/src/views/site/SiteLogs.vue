<template>
	<CardWithDetails
		title="Logs"
		subtitle="Available logs for your site"
		:showDetails="logName"
	>
		<div v-if="$resources.logs.data && $resources.logs.data.length">
			<router-link
				class="block cursor-pointer rounded-md px-2.5"
				:class="logName === log.name ? 'bg-gray-100' : 'hover:bg-gray-50'"
				v-for="log in $resources.logs.data"
				:key="log.name"
				:to="`/sites/${site.name}/logs/${log.name}`"
			>
				<ListItem
					:title="log.name"
					:description="`${formatDate(log.modified) + '\n' + log.size} kB`"
				/>
				<div class="border-b"></div>
			</router-link>
		</div>
		<div v-else>
			<Button
				v-if="$resources.logs.loading"
				:loading="true"
				loading-text="Loading..."
			/>
			<span v-else class="text-base text-gray-600">No logs</span>
		</div>
		<template #details>
			<SiteLogsDetail :site="site" :logName="logName" />
		</template>
	</CardWithDetails>
</template>

<script>
import CardWithDetails from '@/components/CardWithDetails.vue';
import SiteLogsDetail from './SiteLogsDetail.vue';
export default {
	name: 'SiteLogs',
	props: ['site', 'logName'],
	components: { CardWithDetails, SiteLogsDetail },
	resources: {
		logs() {
			return {
				method: 'press.api.site.logs',
				params: { name: this.site?.name },
				auto: true
			};
		}
	}
};
</script>
