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
			type="combobox"
			label="Choose GitHub User / Organization"
			:options="
				options.installations.map((i) => ({
					label: i.login,
					value: String(i.id), // type cast to string for search to work
					image: i.image,
				}))
			"
			:modelValue="selectedGithubUser?.value"
			@update:modelValue="
				(optionValue) => {
					selectedGithubUser = options.installations.find(
						(option) => String(option.id) === optionValue,
					);
				}
			"
		>
			<template #prefix>
				<img
					v-if="selectedGithubUserData"
					:src="selectedGithubUserData?.image"
					class="mr-2 h-4 w-4 rounded-full"
				/>
				<FeatherIcon v-else name="users" class="mr-2 h-4 w-4" />
			</template>
			<template #item-prefix="{ active, selected, option }">
				<img
					v-if="option?.image"
					:src="option.image"
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
			type="combobox"
			v-if="selectedGithubUserData"
			label="Choose GitHub Repository"
			:options="
				(selectedGithubUserData.repos || []).map((r) => ({
					label: r.name,
					value: r.name,
				}))
			"
			:modelValue="selectedGithubRepository?.value"
			@update:modelValue="
				(optionValue) => {
					selectedGithubRepository = (selectedGithubUserData.repos || []).find(
						(option) => option.name === optionValue,
					);
				}
			"
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

		<p v-if="selectedGithubUserData" class="!mt-2 text-sm text-gray-600">
			Don't see your repository here?
			<Link :href="selectedGithubUserData.url" class="font-medium">
				Add from GitHub
			</Link>
		</p>

		<div v-if="selectedGithubRepository" class="space-y-1.5">
			<div class="text-xs text-ink-gray-5">Choose Branch</div>
			<Combobox
				v-if="selectedGithubRepository"
				allow-custom-value
				:options="branchOptions"
				:modelValue="selectedBranch?.value"
				@update:modelValue="onChangeBranchDebounce"
			>
				<template #prefix>
					<FeatherIcon name="git-branch" class="mr-2 h-4 w-4" />
				</template>
			</Combobox>
		</div>
	</div>
</template>

<script>
import { Combobox, debounce } from 'frappe-ui';

export default {
	components: {
		Combobox,
	},
	emits: ['validateApp', 'fieldChange'],
	data() {
		return {
			app: {},
			selectedBranch: null,
			selectedGithubUser: null,
			selectedGithubRepository: null,
		};
	},
	watch: {
		selectedGithubUser() {
			this.selectedBranch = '';
			this.$emit('fieldChange');
		},
		selectedGithubRepository(repo) {
			if (!repo) {
				this.selectedBranch = '';
				return;
			}
			this.$emit('fieldChange');
			this.$resources.branches.submit({
				owner: this.selectedGithubUser?.login,
				name: repo?.name,
				installation: this.selectedGithubUser?.id,
			});

			if (this.selectedGithubUserData) {
				let defaultBranch = this.selectedGithubUserData.repos.find(
					(r) => r.name === repo.name,
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
					selectedGithubUser: this.selectedGithubUserData,
				});
		},
	},
	resources: {
		options() {
			return {
				url: 'press.api.github.options',
				auto: true,
			};
		},
		branches() {
			return {
				url: 'press.api.github.branches',
			};
		},
		clearAccessToken() {
			return {
				url: 'press.api.github.clear_token_and_get_installation_url',
				onSuccess(installation_url) {
					window.location.href = installation_url + '?state=' + this.state;
				},
			};
		},
	},
	computed: {
		options() {
			return this.$resources.options.data;
		},
		appOwner() {
			return this.selectedGithubUser?.login;
		},
		appName() {
			return this.selectedGithubRepository?.name;
		},
		branchOptions() {
			return (this.$resources.branches.data || []).map((branch) => ({
				label: branch.name,
				value: branch.name,
			}));
		},
		selectedGithubUserData() {
			if (!this.selectedGithubUser) return null;
			return this.options.installations.find(
				(i) => i.id === Number(this.selectedGithubUser.id),
			);
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
			return this.$resources.options?.error?.messages.includes(
				'Bad credentials',
			);
		},
		state() {
			let location = window.location.href;
			let state = { team: this.$team.name, url: location };
			return btoa(JSON.stringify(state));
		},
	},
	created() {
		this.onChangeBranchDebounce = debounce((val) => {
			this.selectedBranch = { label: val, value: val };
		}, 500);
	},
};
</script>
