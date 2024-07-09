<template>
	<Dialog
		:options="{
			title: 'Add a new Marketplace App',
			size: 'xl',
			actions: [
				{
					label: 'Add App',
					variant: 'solid',
					disabled: !appValidated && !selectedVersion,
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
			<GitHubAppSelector
				class="pt-2"
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
			<LinkControl
				v-if="selectedBranch"
				class="mt-4"
				type="autocomplete"
				label="Choose Version"
				:options="{ doctype: 'Frappe Version', filters: { public: 1 } }"
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
			<ErrorMessage :message="$resources.validateApp.error" />
		</template>
	</Dialog>
</template>

<script>
import { toast } from 'vue-sonner';
import GitHubAppSelector from '../GitHubAppSelector.vue';
import LinkControl from '../LinkControl.vue';

export default {
	components: {
		GitHubAppSelector,
		LinkControl
	},
	data() {
		return {
			show: true,
			app: {},
			selectedBranch: '',
			selectedVersion: '',
			appValidated: false,
			selectedGithubUser: null,
			selectedGithubRepository: null
		};
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

					const repo_owner = this.selectedGithubUser?.label;
					const repo = data.name;
					const repository_url = `https://github.com/${repo_owner}/${repo}`;

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
		addApp() {
			return {
				url: 'press.api.client.insert',
				makeParams() {
					return {
						doc: {
							...this.app,
							doctype: 'Marketplace App',
							version: this.selectedVersion
						}
					};
				}
			};
		}
	},
	methods: {
		addApp() {
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
