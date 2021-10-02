<template>
	<div class="grid grid-cols-1 gap-5 md:grid-cols-2">
		<Card
			title="Site Activity"
			subtitle="Log of activities performed on your site"
		>
			<div class="divide-y">
				<ListItem
					v-for="a in activities.data"
					:key="a.creation"
					:title="`${a.action} by ${a.owner}`"
					:description="getDescription(a)"
				/>
			</div>
			<div class="my-2" v-if="!$resources.activities.lastPageEmpty">
				<Button
					:loading="$resources.activities.loading"
					loadingText="Fetching..."
					@click="pageStart += 20"
				>
					Load more
				</Button>
			</div>
		</Card>
	</div>
</template>

<script>
export default {
	name: 'SiteActivity',
	props: ['site'],
	resources: {
		activities() {
			return {
				method: 'press.api.site.activities',
				params: {
					name: this.site.name,
					start: this.pageStart
				},
				auto: true,
				paged: true,
				keepData: true
			};
		}
	},
	data() {
		return {
			pageStart: 0
		};
	},
	methods: {
		getDescription(activity) {
			let description = '';
			if (activity.reason) {
				description += `Reason: ${activity.reason}\n`;
			}
			description += this.formatDate(activity.creation);
			return description;
		}
	}
};
</script>
