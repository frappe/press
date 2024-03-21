<template>
	<Dialog
		:options="{
			title: 'Add a new app',
			size: 'xl',
			actions: [
				{
					label: 'Add App',
					variant: 'solid',
					onClick() {
						app.version = selectedVersion.value || options.versions[0].name;
						$emit('app-added', app);
						show = false;
					}
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
			<FTabs
				class="[&>div]:pl-0"
				:tabs="tabs"
				v-model="tabIndex"
				v-slot="{ tab }"
			>
				<div class="-ml-0.5 pl-1">
					<div v-if="tab.value === 'public-github-app'" class="space-y-4">
						<div class="mt-4 flex items-end space-x-2">
							<FormControl
								class="mb-0.5 grow"
								label="GitHub URL"
								v-model="githubAppLink"
								autocomplete="off"
							/>
							<Button
								v-if="!selectedBranch"
								label="Fetch Branches"
								:loading="$resources.branches.loading"
								@click="
									$resources.branches.submit({
										owner: appOwner,
										name: appName
									})
								"
							/>
							<Autocomplete
								v-else
								:options="branchOptions"
								v-model="selectedBranch"
							>
								<template v-slot:target="{ togglePopover }">
									<Button
										:label="selectedBranch?.value || selectedBranch"
										icon-right="chevron-down"
										@click="() => togglePopover()"
									/>
								</template>
							</Autocomplete>
						</div>
					</div>
					<div v-else-if="tab.value === 'your-github-app'" class="pt-4">
						<div
							v-if="$resources.options.loading"
							class="mt-2 flex justify-center"
						>
							<LoadingText />
						</div>
						<div
							class="flex justify-center pt-2"
							v-else-if="!options?.authorized"
						>
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
							<FormControl
								v-if="showVersionSelector"
								type="autocomplete"
								label="Choose Version"
								:options="options.versions.map(v => v.name)"
								v-model="selectedVersion"
							/>
						</div>
					</div>
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
				</div>
			</FTabs>
			<ErrorMessage
				:message="$resources.validateApp.error || $resources.branches.error"
			/>
		</template>
	</Dialog>
</template>

<script>
import { FormControl, Tabs } from 'frappe-ui';

export default {
	name: 'NewAppDialog',
	components: {
		FTabs: Tabs,
		FormControl
	},
	props: {
		showVersionSelector: {
			type: Boolean,
			default: false
		}
	},
	emits: ['app-added'],
	data() {
		return {
			show: true,
			app: null,
			tabIndex: 0,
			githubAppLink: '',
			selectedBranch: '',
			selectedVersion: '',
			appValidated: false,
			requiresReAuth: false,
			selectedGithubUser: null,
			selectedGithubRepository: null,
			tabs: [
				{
					label: 'Public GitHub App',
					value: 'public-github-app'
				},
				{
					label: 'Your GitHub App',
					value: 'your-github-app'
				}
			]
		};
	},
	watch: {
		tabIndex() {
			this.app = null;
			this.appValidated = false;
			this.selectedBranch = '';
			this.githubAppLink = '';
			this.selectedGithubUser = null;
			this.selectedGithubRepository = null;
			this.$resources.branches.reset();
		},
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
					if (data) {
						this.app = {
							name: data.name,
							title: data.title,
							repository_url:
								this.githubAppLink ||
								`https://github.com/${this.selectedGithubUser.label}/${data.name}`,
							branch: this.selectedBranch.value
						};
					}
				}
			};
		},
		branches() {
			return {
				url: 'press.api.github.branches',
				onSuccess(branches) {
					if (this.githubAppLink)
						this.selectedBranch = {
							label: branches[0].name,
							value: branches[0].name
						};
					this.$resources.validateApp.submit({
						owner: this.appOwner,
						repository: this.appName,
						branch: branches[0].name,
						installation: this.selectedGithubUser?.value?.id
					});
				},
				validate() {
					const githubUrlRegex =
						/^(https?:\/\/)?(www\.)?github\.com\/([a-zA-Z0-9_.\-]+)\/([a-zA-Z0-9_.\-]+)(\/)?$/;
					const isValidUrl = githubUrlRegex.test(this.githubAppLink);

					if (this.tabIndex === 0 && !isValidUrl) {
						return 'Please enter a valid github link';
					}
				}
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
			if (this.tabIndex === 1) {
				return this.selectedGithubUser?.label;
			} else {
				return this.githubAppLink.split('/')[3];
			}
		},
		appName() {
			if (this.tabIndex === 1) {
				return this.selectedGithubRepository?.label;
			} else {
				return this.githubAppLink.split('/')[4].replace('.git', '');
			}
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
	}
};
</script>
