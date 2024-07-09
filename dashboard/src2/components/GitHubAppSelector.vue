<template>
	<div v-if="$resources.options.loading" class="mt-2 flex justify-center">
		<LoadingText />
	</div>
	<div class="flex justify-center pt-2" v-else-if="!options?.authorized">
		<Button
			v-if="requiresReAuth"
			variant="solid"
			icon-left="github"
			label="Re-authorize GitHub"
			@click="$resources.clearAccessToken.submit()"
			:loading="$resources.clearAccessToken.loading"
		/>
		<Button
			v-if="needsAuthorization"
			variant="solid"
			icon-left="github"
			label="Connect To GitHub"
			:link="options.installation_url + '?state=' + state"
		/>
	</div>
	<div v-else class="space-y-4">
		<FormControl
			type="autocomplete"
			label="Choose GitHub User / Organization"
			:options="
				options.installations.map(i => ({
					label: i.login,
					value: i
				}))
			"
			v-model="selectedGithubUser"
		>
			<template #prefix>
				<img
					v-if="selectedGithubUser"
					:src="selectedGithubUser?.value?.image"
					class="mr-2 h-4 w-4 rounded-full"
				/>
				<FeatherIcon v-else name="users" class="mr-2 h-4 w-4" />
			</template>
			<template #item-prefix="{ active, selected, option }">
				<img
					v-if="option.value?.image"
					:src="option.value.image"
					class="mr-2 h-4 w-4 rounded-full"
				/>
				<FeatherIcon v-else name="user" class="mr-2 h-4 w-4" />
			</template>
		</FormControl>
		<span class="text-sm text-gray-600">
			Don't see your organization?
			<Link
				:href="options.installation_url + '?state=' + state"
				class="font-medium"
			>
				Add from GitHub
			</Link>
		</span>
		<FormControl
			type="autocomplete"
			v-if="selectedGithubUser"
			label="Choose GitHub Repository"
			:options="
				(selectedGithubUser.value.repos || []).map(r => ({
					label: r.name,
					value: r.name
				}))
			"
			v-model="selectedGithubRepository"
		>
			<template #prefix>
				<FeatherIcon name="book" class="mr-2 h-4 w-4" />
			</template>
			<template #item-prefix="{ active, selected, option }">
				<FeatherIcon
					:name="option.value.private ? 'lock' : 'book'"
					class="mr-2 h-4 w-4"
				/>
			</template>
		</FormControl>

		<p v-if="selectedGithubUser" class="!mt-2 text-sm text-gray-600">
			Don't see your repository here?
			<Link :href="selectedGithubUser.value.url" class="font-medium">
				Add from GitHub
			</Link>
		</p>
		<FormControl
			v-if="selectedGithubRepository"
			type="autocomplete"
			label="Choose Branch"
			:options="branchOptions"
			v-model="selectedBranch"
		>
			<template #prefix>
				<FeatherIcon name="git-branch" class="mr-2 h-4 w-4" />
			</template>
		</FormControl>
	</div>
</template>

<script>
export default {
	emits: ['validateApp', 'fieldChange'],
	data() {
		return {
			app: {},
			selectedBranch: '',
			selectedGithubUser: null,
			selectedGithubRepository: null
		};
	},
	watch: {
		selectedGithubUser() {
			this.selectedBranch = '';
			this.$emit('fieldChange');
		},
		selectedGithubRepository(val) {
			this.$emit('fieldChange');
			this.$resources.branches.submit({
				owner: this.selectedGithubUser?.label,
				name: val?.label,
				installation: this.selectedGithubUser?.value.id
			});

			if (this.selectedGithubUser) {
				let defaultBranch = this.selectedGithubUser.value.repos.find(
					r => r.name === val.label
				).default_branch;
				this.selectedBranch = { label: defaultBranch, value: defaultBranch };
			} else this.selectedBranch = '';
		},
		selectedBranch(newSelectedBranch) {
			if (this.appOwner && this.appName && newSelectedBranch)
				this.$emit('validateApp', {
					owner: this.appOwner,
					repository: this.appName,
					branch: newSelectedBranch.value,
					selectedGithubUser: this.selectedGithubUser
				});
		}
	},
	resources: {
		options() {
			return {
				url: 'press.api.github.options',
				auto: true,
				onError(error) {
					if (error.messages.includes('Bad credentials')) {
						this.requiresReAuth = true;
					}
				}
			};
		},
		branches() {
			return {
				url: 'press.api.github.branches'
			};
		},
		clearAccessToken() {
			return {
				url: 'press.api.github.clear_token_and_get_installation_url',
				onSuccess(installation_url) {
					window.location.href = installation_url + '?state=' + this.state;
				}
			};
		}
	},
	computed: {
		options() {
			return this.$resources.options.data;
		},
		appOwner() {
			return this.selectedGithubUser?.label;
		},
		appName() {
			return this.selectedGithubRepository?.label;
		},
		branchOptions() {
			return (this.$resources.branches.data || []).map(branch => ({
				label: branch.name,
				value: branch.name
			}));
		},
		needsAuthorization() {
			if (this.$resources.options.loading) return false;
			return (
				this.$resources.options.data &&
				(!this.$resources.options.data.authorized ||
					this.$resources.options.data.installations.length === 0)
			);
		},
		requiresReAuth() {
			return this.options?.error?.message === 'Bad credentials';
		},
		state() {
			let location = window.location.href;
			let state = { team: this.$team.name, url: location };
			return btoa(JSON.stringify(state));
		}
	}
};
</script>
