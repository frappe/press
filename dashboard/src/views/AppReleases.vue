<template>
	<div>
		<Section
			title="Releases"
			description="Everything you have pushed to GitHub"
		>
			<SectionCard class="md:w-2/3">
				<div v-if="releases.data">
					<div
						class="text-base cursor-pointer items-center px-6 py-3 hover:bg-gray-50"
						v-for="release in releases.data"
						:key="release.name"
						@click="
							showDetailsForRelease =
								showDetailsForRelease === release ? null : release
						"
					>
						<div class="flex justify-between">
							<div class="pr-2 font-mono">
								{{ release.hash.slice(0, 6) }}
							</div>
							<div class="flex-1 pr-2 truncate font-semibold">
								{{ release.message }}
							</div>
							<FormatDate>{{ release.creation }}</FormatDate>
							<FeatherIcon
								:name="
									showDetailsForRelease === release
										? 'chevron-up'
										: 'chevron-down'
								"
								class="w-4 h-4 ml-2"
							/>
						</div>
						<div v-show="showDetailsForRelease === release" class="py-4">
							<div class="flex items-center justify-between">
								<div>
									<Badge :color="color(release.status)" v-if="release.status">
										{{ release.status }}
									</Badge>
								</div>
								<div class="flex items-center" v-if="release.tags">
									<span>Tags:</span>
									<Badge
										v-for="(tag, index) in release.tags"
										:key="index"
										class="mr-2"
									>
										{{ tag }}
									</Badge>
								</div>
							</div>
							<div class="mt-4">
								<Button
									v-if="release.status == 'Approved'"
									type="primary"
									@click="deploy(release)"
									>Deploy</Button
								>
								<Button
									v-if="release.status == ''"
									type="primary"
									@click="request_approval(release)"
									>Request Approval</Button
								>
							</div>
							<div v-if="release.status == 'Rejected'">
								Reason:
								<span class="text-red-600">{{ release.reason }}</span>
								<span class="text-red-600" v-html="release.comments"></span>
							</div>
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
	data() {
		return {
			showDetailsForRelease: null
		};
	},
	methods: {
		color(status) {
			let color = {
				'Awaiting Approval': 'orange',
				Running: 'yellow',
				Approved: 'green',
				Rejected: 'red'
			}[status];
			return color;
		},
		async deploy(release) {
			let result = await this.$call('press.api.app.deploy', {
				name: this.app.name,
				release: release.name
			});
			this.$router.push(`/apps/depoys/${result.name}`);
		}
	},
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
