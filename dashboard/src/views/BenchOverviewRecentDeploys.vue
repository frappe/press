<template>
	<Card
		title="Recent deploys"
		subtitle="History of deploys on your bench"
		:loading="$resources.recentDeploys.loading"
		v-if="$resources.recentDeploys.data && $resources.recentDeploys.data.length"
	>
		<template #actions>
			<router-link
				class="text-base text-blue-500 hover:text-blue-600"
				:to="`/benches/${bench.name}/deploys`"
			>
				View deploys →
			</router-link>
		</template>
		<div class="divide-y">
			<ListItem
				v-for="deploy in $resources.recentDeploys.data"
				:key="deploy.name"
				:title="`Deploy on ${formatDate(deploy.creation)}`"
			/>
		</div>
	</Card>
</template>
<script>
export default {
	name: 'BenchOverviewRecentDeploys',
	props: ['bench'],
	resources: {
		recentDeploys() {
			return {
				method: 'press.api.bench.recent_deploys',
				params: {
					name: this.bench?.name
				},
				auto: true
			};
		}
	}
};
</script>
