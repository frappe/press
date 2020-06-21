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
						v-for="(release, index) in releases.data"
						:key="release.name"
					>
						<div class="flex justify-between items-center">
							<div class="pr-2 font-mono">
								{{ release.hash.slice(0, 6) }}
							</div>
							<div class="flex-1 pr-2 truncate font-semibold">
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
							<div class="w-32">
								<Badge
									v-if="
										(index === 0 && release.status != 'Approved') ||
											release.status === 'Rejected'
									"
									:status="release.status"
								>
									{{ release.status }}
								</Badge>
								<Button
									v-if="
										index === 0 &&
											release.status == 'Approved' &&
											!release.deployable
									"
									type="primary"
									@click="$resources.deploy.fetch()"
									:disabled="$resources.deploy.loading"
									>Deploy</Button
								>
							</div>
						</div>
						<div class="" v-if="release.status == 'Rejected'">
							<div>
								Reason:
								<span class="text-red-600">{{ release.reason }}</span>
							</div>
							<div class="text-red-400 ml-4" v-html="release.comments"></div>
						</div>
					</div>
				</div>
				<div class="px-6 mt-2 text-base text-gray-600" v-else>
					No releases found. Push something.
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
		deploy() {
			return {
				method: 'press.api.app.deploy',
				params: {
					name: this.app.name
				},
				onSuccess: () => {
					this.$router.push(`/apps/${this.app.name}/deploys`);
				}
			};
		},
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
