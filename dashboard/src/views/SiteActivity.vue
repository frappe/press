<template>
	<div>
		<Section
			title="Site Activity"
			description="Log of activities performed on your site"
		>
			<SectionCard>
				<div
					class="px-6 py-3 text-base hover:bg-gray-50"
					v-for="a in activities.data"
					:key="a.creation"
				>
					<div>
						{{ a.action }} <span class="text-gray-800">by {{ a.owner }}</span>
					</div>
					<div class="mb-1 text-sm text-gray-800" v-if="a.reason">
						<span class="font-semibold">Reason:</span>
						{{ a.reason }}
					</div>
					<div class="text-sm text-gray-600">
						<FormatDate>
							{{ a.creation }}
						</FormatDate>
					</div>
				</div>
				<div class="px-6 my-2" v-if="!$resources.activities.lastPageEmpty">
					<Button
						:loading="$resources.activities.loading"
						loadingText="Fetching..."
						@click="pageStart += 20"
					>
						Load more
					</Button>
				</div>
			</SectionCard>
		</Section>
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
