<template>
	<Card
		title="Recent activity"
		subtitle="History of recent activities performed on your site"
	>
		<template #actions>
			<Link class="text-base" :href="`#/sites/${site.name}/activity`">
				All activity →
			</Link>
		</template>
		<div class="divide-y">
			<div
				class="py-2"
				v-for="activity in recentActivity"
				:key="activity.name"
			>
				<div class="text-base font-medium text-gray-900">
					{{ activity.action }} by {{ activity.owner }}
				</div>
				<div class="mt-1 text-base text-gray-600">
					<FormatDate>{{ activity.creation }}</FormatDate>
				</div>
			</div>
		</div>
	</Card>
</template>
<script>
export default {
	name: 'SiteOverviewRecentActivity',
	props: ['site', 'recentActivity']
};
</script>
