<template>
	<div>
		<div v-for="installation in options.installations" :key="installation.id">
			<details class="cursor-pointer">
				<summary
					class="flex w-full select-none items-center space-x-2 rounded px-2 py-3 text-base hover:bg-gray-50"
				>
					<img
						class="h-6 w-6 rounded bg-blue-100 object-cover"
						:src="installation.image"
						:alt="`${installation.login} image`"
					/>
					<span>
						{{ installation.login }}
					</span>
				</summary>
				<div class="mb-4 ml-4">
					<button
						class="w-full rounded-md border-2 px-3 py-2 text-base text-gray-900 focus:outline-none"
						:class="
							selectedRepo === repo
								? 'border-blue-500 bg-blue-50'
								: 'border-transparent hover:bg-gray-50'
						"
						v-for="repo in installation.repos"
						:key="repo.id"
						@click="selectRepo(repo, installation)"
					>
						<div class="flex w-full items-center">
							<FeatherIcon
								:name="repo.private ? 'lock' : 'book'"
								class="mr-2 h-4 w-4"
							/>
							<span class="text-lg font-medium">
								{{ repo.name }}
							</span>
							<button
								class="ml-auto"
								v-if="selectedRepo === repo"
								@click.stop="selectRepo(null, null)"
							>
								<FeatherIcon name="x" class="h-4 w-4" />
							</button>
						</div>
						<div v-show="selectedRepo === repo">
							<Dropdown class="mt-2 ml-6 text-left" :items="branchOptions">
								<template v-slot="{ toggleDropdown }">
									<Button
										type="white"
										:loading="repositoryResource.loading"
										loadingText="Loading branches..."
										@click="toggleDropdown()"
										icon-right="chevron-down"
									>
										{{ selectedBranch || 'Select branch' }}
									</Button>
								</template>
							</Dropdown>
						</div>
					</button>
					<p class="mt-4 text-sm text-gray-700">
						Don't see your repository here?
						<Link :to="installation.url" class="font-medium">
							Add from GitHub
						</Link>
					</p>
				</div>
			</details>
		</div>
	</div>
</template>
<script>
export default {
	name: 'NewAppRepositories',
	props: [
		'options',
		'repositoryResource',
		'selectedRepo',
		'selectedInstallation',
		'selectedBranch'
	],
	methods: {
		selectRepo(repo, installation) {
			if (repo === this.selectedRepo) return;
			this.$emit('update:selectedRepo', repo);
			this.$emit('update:selectedInstallation', installation);
			this.$emit('update:selectedBranch', null);
		}
	},
	computed: {
		branchOptions() {
			if (this.repositoryResource.loading || !this.repositoryResource.data) {
				return [];
			}
			return (this.repositoryResource.data.branches || []).map(d => {
				return {
					label: d.name,
					action: () => this.$emit('update:selectedBranch', d.name)
				};
			});
		}
	}
};
</script>
