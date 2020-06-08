<template>
	<div>
		<Section
			title="Releases"
			description="Everything you have pushed to GitHub"
		>
			<SectionCard class="sm:w-1/2">
				<div v-if="app.releases">
					<div
						class="block px-6 py-4 text-base hover:bg-gray-50"
						v-for="release in app.releases"
						:key="release.name"
					>
						<div class="w-full">
							<div class="font-semibold">
								{{ release.message }}
							</div>
							<div>
								{{ release.hash.slice(0, 10) }}
							</div>
							<div>
								{{ release.author }}
							</div>
							<Badge
								v-for="(tag, index) in release.tags"
								:key="index"
								class="mr-2 mt-2"
							>
								{{ tag }}
							</Badge>
							<Badge class="ml-4" :color="color(release.status)">{{
								release.status
							}}</Badge>
							<div v-if="release.status == 'Rejected'">
								{{ release.reason }}
							</div>
							<div class="font-semibold">
								<span>
									Release on <FormatDate>{{ release.creation }}</FormatDate>
								</span>
							</div>
							<Button
								v-if="release.status == 'Approved'"
								@click="deploy(release.name)"
								>Deploy</Button
							>
							<Button
								v-if="release.status == ''"
								@click="request_approval(release.name)"
								>Request Approval</Button
							>
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
	methods: {
		color(status) {
			let color = {
				'Awaiting Approval': 'orange',
				Running: 'yellow',
				Approved: 'green',
				Rejected: 'red'
			}[status];
			return color;
		}
	}
};
</script>
