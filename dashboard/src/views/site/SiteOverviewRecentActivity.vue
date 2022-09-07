<template>
	<Card
		title="Recent activity"
		subtitle="History of recent activities performed on your site"
	>
		<template #actions>
			<Link class="text-base" :to="`/sites/${site.name}/activity`">
				All activity →
			</Link>
		</template>
		<div class="divide-y">
			<ListItem
				v-for="activity in recentActivity"
				:key="activity.name"
				:title="`${activity.action} by ${activity.owner}`"
				:description="formatDate(activity.creation)"
			/>
		</div>
	</Card>
</template>
<script>
export default {
	name: 'SiteOverviewRecentActivity',
	props: ['site', 'recentActivity']
};
</script>
