<template>
	<Dialog
		:options="{
			title: 'Add a new Marketplace App',
			size: 'xl',
			actions: [
				{
					label: 'Add App',
					variant: 'solid',
					onClick: addApp
				}
			]
		}"
		v-model="show"
		@update:modelValue="
			() => {
				show = false;
			}
		"
	>
		<template #body-content>
			<div class="pt-4">
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
							selectedGithubUser.value.repos.map(r => ({
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
			</div>
			<FormControl
				v-if="selectedBranch"
				class="mt-4"
				type="autocomplete"
				label="Choose Version"
				:options="options.versions.map(v => v.name)"
				v-model="selectedVersion"
			/>
			<div class="mt-4 space-y-2">
				<div
					v-if="$resources.validateApp.loading && !appValidated"
					class="flex text-base text-gray-700"
				>
					<LoadingIndicator class="mr-2 w-4" />
					Validating app...
				</div>
				<div v-if="appValidated" class="flex text-base text-gray-700">
					<GreenCheckIcon class="mr-2 w-4" />
					Found {{ this.app.title }} ({{ this.app.name }})
				</div>
			</div>
			<ErrorMessage
				:message="$resources.validateApp.error || $resources.branches.error"
			/>
		</template>
	</Dialog>
</template>

<script>
import { toast } from 'vue-sonner';

export default {
	data() {
		return {
			show: true,
			app: {},
			githubAppLink: '',
			selectedBranch: '',
			selectedVersion: '',
			appValidated: false,
			requiresReAuth: false,
			selectedGithubUser: null,
			selectedGithubRepository: null
		};
	},
	watch: {
		githubAppLink() {
			this.selectedBranch = '';
			this.appValidated = false;
		},
		selectedGithubUser() {
			this.selectedBranch = '';
			this.appValidated = false;
		},
		selectedGithubRepository(val) {
			this.appValidated = false;
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
				this.$resources.validateApp.submit({
					owner: this.appOwner,
					repository: this.appName,
					branch: newSelectedBranch.value,
					installation: this.selectedGithubUser?.value?.id
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
		validateApp() {
			return {
				url: 'press.api.github.app',
				onSuccess(data) {
					this.appValidated = true;
					if (!data) {
						return;
					}

					let repository_url = this.githubAppLink;
					if (!repository_url) {
						var repo = this.selectedGithubRepository?.label || data.name;
						repository_url = `https://github.com/${this.selectedGithubUser.label}/${repo}`;
					}

					this.app = {
						name: data.name,
						title: data.title,
						repository_url,
						github_installation_id: this.selectedGithubUser?.value.id,
						branch: this.selectedBranch.value
					};
				}
			};
		},
		branches() {
			return {
				url: 'press.api.github.branches',
				initialData: []
			};
		},
		clearAccessToken() {
			return {
				url: 'press.api.github.clear_token_and_get_installation_url',
				onSuccess(installation_url) {
					window.location.href = installation_url + '?state=' + this.state;
				}
			};
		},
		addApp() {
			return {
				url: 'press.api.client.insert',
				makeParams() {
					return {
						doc: { ...this.app, doctype: 'Marketplace App' }
					};
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
		state() {
			let location = window.location.href;
			let state = { team: this.$team.name, url: location };
			return btoa(JSON.stringify(state));
		}
	},
	methods: {
		addApp() {
			this.app.version =
				this.selectedVersion.value || this.options.versions[0].name;
			this.app.branch = this.selectedBranch.value;

			toast.promise(this.$resources.addApp.submit(), {
				loading: 'Adding new app...',
				success: () => {
					this.show = false;
					this.$router.push({
						name: 'Marketplace App Detail Listing',
						params: { name: this.app.name }
					});
					return 'New app added';
				},
				error: e => {
					return e.messages.length ? e.messages.join('\n') : e.message;
				}
			});
		}
	}
};
</script>
