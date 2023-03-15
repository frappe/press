<template>
	<Dialog
		:modelValue="show"
		:options="{ title: 'Add a New App Version' }"
		@close="
			() => {
				$emit('close', true);
			}
		"
	>
		<template v-slot:body-content>
			<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
				<div>
					<span class="mb-2 block text-sm leading-4 text-gray-700">
						Version
					</span>
					<select class="form-select block w-full" v-model="selectedVersion">
						<option v-for="version in versions" :key="version">
							{{ version }}
						</option>
					</select>
				</div>
				<div>
					<span class="mb-2 block text-sm leading-4 text-gray-700">
						Branch
					</span>
					<select class="form-select block w-full" v-model="selectedBranch">
						<option v-for="branch in branchList()" :key="branch">
							{{ branch }}
						</option>
					</select>
				</div>
			</div>
		</template>
		<template v-slot:actions>
			<Button
				class="mt-3"
				appearance="primary"
				:loading="$resources.addVersion.loading"
				@click="$resources.addVersion.submit()"
				>Add New Version</Button
			>
		</template>
	</Dialog>
</template>

<script>
export default {
	name: 'CreateMarketplaceAppVersion.vue',
	data() {
		return {
			versionList: [],
			branches: [],
			selectedBranch: null,
			selectedVersion: null
		};
	},
	props: ['app', 'show'],
	resources: {
		options() {
			return {
				method: 'press.api.marketplace.options_for_version',
				auto: true,
				params: {
					name: this.app.name,
					source: this.app.sources[0].source
				},
				onSuccess(d) {
					this.versions = d.versions;
					this.branches = d.branches;
				}
			};
		},
		addVersion() {
			return {
				method: 'press.api.marketplace.add_version',
				params: {
					name: this.app.name,
					branch: this.selectedBranch,
					version: this.selectedVersion
				},
				onSuccess() {
					window.location.reload();
				},
				onError(e) {
					this.$notify({
						title: e,
						color: 'red',
						icon: 'x'
					});
				}
			};
		}
	},
	methods: {
		branchList() {
			return this.branches.map(d => d.name);
		}
	}
};
</script>
