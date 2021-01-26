<template>
	<div class="grid grid-cols-1 gap-5 md:grid-cols-2">
		<Card
			title="Site Activity"
			subtitle="Log of activities performed on your site"
		>
			<div class="divide-y">
				<div
					class="py-3 text-base"
					v-for="a in activities.data"
					:key="a.creation"
				>
					<h3 class="text-lg font-medium">
						{{ a.action }} <span class="text-gray-800">by {{ a.owner }}</span>
					</h3>
					<p class="mb-1 text-sm text-gray-800" v-if="a.reason">
						<span class="font-semibold">Reason:</span>
						{{ a.reason }}
					</p>
					<p class="mt-1 text-sm text-gray-600">
						<FormatDate>
							{{ a.creation }}
						</FormatDate>
					</p>
				</div>
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
	}
};
</script>
