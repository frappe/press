<template>
	<Dialog
		:options="{
			title: 'Add a new Marketplace App',
			size: 'xl',
			actions: [
				{
					label: 'Add App',
					variant: 'solid',
					disabled: (!appValidated && !selectedVersion) || !this.app.is_public,
					onClick: addApp,
				},
			],
		}"
		v-model="show"
		@update:modelValue="
			() => {
				show = false;
			}
		"
	>
		<template #body-content>
			<GitHubAppSelector
				class="pt-2"
				@validateApp="validateApp"
				@fieldChange="appValidated = false"
			/>
			<div class="mt-4 space-y-2">
				<div
					v-if="$resources.validateApp.loading && !appValidated"
					class="flex text-base text-gray-700"
				>
					<LoadingIndicator class="mr-2 w-4" />
					Validating app...
				</div>
				<div
					v-if="appValidated"
					class="flex flex-col text-base text-gray-700 space-y-2"
				>
					<div v-if="this.app.is_public" class="flex items-center gap-2">
						<FeatherIcon
							class="w-4 p-0.5 text-white rounded bg-green-500"
							name="check"
							:stroke-width="3"
						/>
						<span>
							Found <strong>{{ this.app.title }}</strong> ({{ this.app.name }}).
							We will automatically find the compatible Frappe version for this
							app.
						</span>
					</div>
					<div v-else>
						<div class="flex items-center gap-2">
							<FeatherIcon
								class="w-4 p-0.5 text-white rounded bg-red-500"
								name="x"
							/>
							<span>
								The GitHub repository is private. Please ensure the repository
								is public to proceed.
							</span>
						</div>
						<Link
							href="https://frappecloud.com/marketplace/terms"
							class="font-medium text-blue-600 hover:underline"
						>
							Read our Terms and Policy
						</Link>
					</div>
				</div>
			</div>
			<ErrorMessage :message="$resources.validateApp.error" />
		</template>
	</Dialog>
</template>

<script>
import { toast } from 'vue-sonner';
import GitHubAppSelector from '../GitHubAppSelector.vue';
import LinkControl from '../LinkControl.vue';
import { getToastErrorMessage } from '../../utils/toast';

export default {
	components: {
		GitHubAppSelector,
		LinkControl,
	},
	data() {
		return {
			show: true,
			app: {},
			selectedBranch: '',
			selectedVersion: '',
			appValidated: false,
			selectedGithubUser: null,
			selectedGithubRepository: null,
		};
	},
	resources: {
		validateApp() {
			return {
				url: 'press.api.github.app',
				onSuccess: async (data) => {
					this.appValidated = true;
					if (!data) {
						return;
					}

					const repo_owner = this.selectedGithubUser?.login;
					const repo = this.selectedGithubRepository || data.name;
					const repository_url = `https://github.com/${repo_owner}/${repo}`;
					this.app = {};
					const isPublic = await this.checkRepoVisibility(repo_owner, repo);

					this.app = {
						name: data.name,
						title: data.title,
						repository_url,
						github_installation_id: this.selectedGithubUser?.id,
						branch: this.selectedBranch.value,
						is_public: isPublic,
					};
				},
			};
		},
		addApp() {
			return {
				url: 'press.api.client.insert',
				makeParams() {
					return {
						doc: {
							...this.app,
							doctype: 'Marketplace App',
							version: this.selectedVersion,
						},
					};
				},
			};
		},
	},
	methods: {
		addApp() {
			toast.promise(this.$resources.addApp.submit(), {
				loading: 'Adding new app...',
				success: () => {
					this.show = false;
					this.$router.push({
						name: 'Marketplace App Detail Listing',
						params: { name: this.app.name },
					});
					return 'New app added';
				},
				error: (e) => getToastErrorMessage(e),
			});
		},
		validateApp(data) {
			this.selectedBranch = {
				label: data.branch,
				value: data.branch,
			};
			this.selectedGithubRepository = data.repository;
			this.selectedGithubUser = data.selectedGithubUser;

			this.$resources.validateApp.submit({
				...data,
				installation: data.selectedGithubUser.id,
			});
		},
		async checkRepoVisibility(owner, repo) {
			try {
				const response = await fetch(
					`https://api.github.com/repos/${owner}/${repo}`,
				);
				if (!response.ok) {
					throw new Error('Repository not found or private');
				}

				const repoData = await response.json();
				return !repoData.private; // Returns true if public, false if private
			} catch (error) {
				console.error(error);
				return false; // Assume false if there was an error
			}
		},
	},
};
</script>
