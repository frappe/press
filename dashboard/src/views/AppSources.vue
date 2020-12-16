<template>
	<div>
		<Section title="Sources" :description="'Sources for your app'">
			<SectionCard>
				<div
					class="px-6 py-3 hover:bg-gray-50 items-center grid grid-cols-3 items-center"
					v-for="source in sources.data"
					:key="source.app"
				>
					<div class="col-span-2">
						<p class="font-semibold  text-base">
							<a
								:href="source.repository_url + '/tree/' + source.branch"
								target="_blank"
								>{{ source.repository_owner }}:{{ source.branch }}</a
							>
						</p>
					</div>
					<div class="flex">
						<p
							class="text-sm text-gray-800 mr-2"
							v-for="version in source.versions"
							:key="version.name"
						>
							{{ version.version }}
						</p>
					</div>
				</div>
			</SectionCard>
		</Section>
	</div>
</template>

<script>
export default {
	name: 'AppSources',
	props: ['app'],
	resources: {
		sources() {
			return {
				method: 'press.api.app.sources',
				params: {
					name: this.app.name
				},
				auto: true
			};
		}
	}
};
</script>
