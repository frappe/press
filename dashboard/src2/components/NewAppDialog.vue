<template>
	<Dialog
		:options="{
			title: 'Add a new app',
			size: 'xl',
			actions: [
				{
					label: 'Add App',
					variant: 'solid',
					disabled: !app || !appValidated,
					onClick() {
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
				<div class="-ml-0.5 p-1">
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
						<GitHubAppSelector
							@validateApp="
								data => {
									selectedBranch = {
										label: data.branch,
										value: data.branch
									};
									selectedGithubRepository = data.repository;
									selectedGithubUser = data.selectedGithubUser;

									$resources.validateApp.submit({
										...data,
										installation: data.selectedGithubUser.value.id
									});
								}
							"
							@fieldChange="appValidated = false"
						/>
					</div>
					<div class="mt-4 space-y-2">
						<div
							v-if="$resources.validateApp.loading && !appValidated"
							class="flex text-base text-gray-700"
						>
							<LoadingIndicator class="mr-2 w-4" />
							Validating app...
						</div>
						<div
							v-if="appValidated && app"
							class="flex text-base text-gray-700"
						>
							<GreenCheckIcon class="mr-2 w-4" />
							Found {{ app.title }} ({{ app.name }})
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
import { DashboardError } from '../utils/error';
import GitHubAppSelector from './GitHubAppSelector.vue';

export default {
	name: 'NewAppDialog',
	components: {
		GitHubAppSelector,
		FTabs: Tabs,
		FormControl
	},
	emits: ['app-added'],
	data() {
		return {
			show: true,
			app: {},
			tabIndex: 0,
			githubAppLink: '',
			selectedBranch: '',
			appValidated: false,
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
						const repo_owner = this.selectedGithubUser?.label;
						const repo = this.selectedGithubRepository || data.name;
						repository_url = `https://github.com/${repo_owner}/${repo}`;
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
				validate() {
					const githubUrlRegex =
						/^(https?:\/\/)?(www\.)?github\.com\/([a-zA-Z0-9_.\-]+)\/([a-zA-Z0-9_.\-]+)(\/)?$/;
					const isValidUrl = githubUrlRegex.test(this.githubAppLink);

					if (!isValidUrl) {
						throw new DashboardError('Please enter a valid github link');
					}
				},
				onSuccess(data) {
					if (this.tabIndex === 0)
						this.selectedBranch = {
							label: data[0].name,
							value: data[0].name
						};
				}
			};
		}
	},
	computed: {
		appOwner() {
			if (this.tabIndex === 0) {
				return this.githubAppLink.split('/')[3];
			}
		},
		appName() {
			if (this.tabIndex === 0) {
				return this.githubAppLink.split('/')[4].replace('.git', '');
			}
		},
		branchOptions() {
			return (this.$resources.branches.data || []).map(branch => ({
				label: branch.name,
				value: branch.name
			}));
		}
	}
};
</script>
