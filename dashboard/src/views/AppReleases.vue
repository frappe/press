<template>
	<div>
		<Section
			title="Releases"
			description="Everything you have pushed to GitHub"
		>
			<SectionCard class="md:w-2/3">
				<div v-if="releases.data">
					<div
						class="text-base items-center px-6 py-3 hover:bg-gray-50"
						v-for="release in releases.data"
						:key="release.name"
					>
						<div class="flex justify-between items-center">
							<div class="pr-2 font-mono">
								{{ release.hash.slice(0, 6) }}
							</div>
							<div class="flex-1 pr-2 truncate">
								{{ release.message }}
							</div>
							<div class="flex items-center" v-if="release.tags">
								<Badge
									v-for="(tag, index) in release.tags"
									:key="index"
									class="mr-2"
								>
									{{ tag }}
								</Badge>
							</div>
						</div>
					</div>
				</div>
			</SectionCard>
		</Section>
	</div>
</template>

<script>
export default {
	name: 'AppReleases',
	props: ['app'],
	resources: {
		releases() {
			return {
				method: 'press.api.app.releases',
				params: {
					name: this.app.name
				},
				auto: true
			};
		}
	}
};
</script>
