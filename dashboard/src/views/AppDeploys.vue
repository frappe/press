<template>
	<div>
		<Section title="Deploys" description="Deploy log of your app">
			<SectionCard class="md:w-2/3">
				<div v-if="deploys.data && deploys.data.length">
					<div
						class="text-base items-center px-6 py-3 hover:bg-gray-50"
						v-for="deploy in deploys.data"
						:key="deploy.name"
					>
						<div class="flex justify-between items-center">
							<div class="pr-2 font-mono">
								{{ deploy.hash.slice(0, 6) }}
							</div>
							<div class="flex-1 pr-2 truncate font-semibold">
								{{ deploy.message }}
							</div>
							<div class="flex items-center" v-if="deploy.tags">
								<Badge
									v-for="(tag, index) in deploy.tags"
									:key="index"
									class="mr-2"
								>
									{{ tag }}
								</Badge>
							</div>
							<div class="w-32">
								<Badge :status="deploy.status">
									{{ deploy.status }}
								</Badge>
							</div>
						</div>
					</div>
				</div>
				<div class="px-6 py-2 text-base text-gray-600" v-else>
					This app isn't deployed yet.
				</div>
			</SectionCard>
		</Section>
	</div>
</template>

<script>
export default {
	name: 'AppDeploys',
	props: ['app'],
	resources: {
		deploys() {
			return {
				method: 'press.api.app.deploys',
				params: {
					name: this.app.name
				},
				auto: true
			};
		}
	}
};
</script>
