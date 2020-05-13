<template>
	<div>
		<Section
			title="Site Activity"
			description="Log of activities performed on your site"
		>
			<SectionCard>
				<div
					class="px-6 py-3 hover:bg-gray-50"
					v-for="a in activities.data"
					:key="a.creation"
				>
					<div>
						{{ a.action }} <span class="text-gray-800">by {{ a.owner }}</span>
					</div>
					<div class="text-sm text-gray-600">
						<FormatDate>
							{{ a.creation }}
						</FormatDate>
					</div>
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
					name: this.site.name
				},
				auto: true
			};
		}
	}
};
</script>
