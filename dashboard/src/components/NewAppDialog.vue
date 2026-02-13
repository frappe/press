<template>
	<Dialog
		:options="{
			title: 'Add app from GitHub',
			size: 'xl',
			actions: [
				{
					label: isAppOnBench
						? 'Update App'
						: $resources.validateApp.loading
							? `Validating branch '${selectedBranch?.value}'`
							: 'Add App',
					variant: 'solid',
					disabled:
						!app ||
						!appValidated ||
						$resources.validateApp.loading ||
						!selectedBranch?.value,
					onClick: addAppHandler,
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
			<FTabs :tabs="tabs" v-model="tabIndex">
				<template #tab-item="{ tab }">
					<div
						class="flex cursor-pointer items-center gap-1.5 py-3 text-base transition"
					>
						{{ tab.label }}
					</div>
				</template>
				<template #tab-panel="{ tab }">
					<div class="-ml-0.5 p-1">
						<div v-if="tab.value === 'public-github-app'" class="space-y-4">
							<div class="mt-4 flex items-end space-x-2">
								<FormControl
									class="grow"
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
											name: appName,
										})
									"
								/>
								<Combobox
									v-else
									:options="branchOptions"
									:modelValue="selectedBranch?.value"
									allow-custom-value
									@update:modelValue="onChangeBranchDebounce"
								/>
							</div>
						</div>
						<div v-else-if="tab.value === 'your-github-app'" class="pt-4">
							<GitHubAppSelector
								@validateApp="validateApp"
								@fieldChange="appValidated = false"
							/>
						</div>
						<div class="mt-4 space-y-2">
							<div
								v-if="$resources.validateApp.loading"
								class="flex text-base text-gray-700"
							>
								<LoadingIndicator class="mr-2 w-4" />
								Validating app...
							</div>
							<div
								v-else-if="appValidated && app"
								class="flex text-base text-gray-700"
							>
								<GreenCheckIcon class="mr-2 w-4" />
								Found {{ app.title }} ({{ app.name }})
							</div>
						</div>
					</div>
				</template>
			</FTabs>
			<AlertBanner
				v-if="isAppOnBench"
				class="mt-4"
				:show-icon="false"
				:title="
					`App <strong>${app.name}</strong> already exists on this Bench. ` +
					`Clicking on Update App will change app source to the selected one.`
				"
				type="warning"
			/>

			<ErrorMessage
				:message="$resources.validateApp.error || $resources.branches.error"
			/>
		</template>
	</Dialog>
</template>

<script>
import { Combobox, debounce, FormControl, Tabs } from 'frappe-ui';
import { DashboardError } from '../utils/error';
import GitHubAppSelector from './GitHubAppSelector.vue';
import AlertBanner from './AlertBanner.vue';

export default {
	name: 'NewAppDialog',
	components: {
		GitHubAppSelector,
		FTabs: Tabs,
		FormControl,
		AlertBanner,
		Combobox,
	},
	props: {
		group: {
			type: Object,
			required: true,
		},
	},
	emits: ['app-added'],
	created() {
		this.onChangeBranchDebounce = debounce((val) => {
			this.selectedBranch = { label: val, value: val };
		}, 500);
	},
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
					value: 'public-github-app',
				},
				{
					label: 'Your GitHub App',
					value: 'your-github-app',
				},
			],
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
			this.$resources.validateApp.reset();
		},
		githubAppLink() {
			this.selectedBranch = '';
			this.appValidated = false;
		},
		selectedBranch(newSelectedBranch) {
			if (this.appOwner && this.appName && newSelectedBranch?.value)
				this.$resources.validateApp.submit({
					owner: this.appOwner,
					repository: this.appName,
					branch: newSelectedBranch.value,
					installation: this.selectedGithubUser?.id,
				});
		},
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
						const repo_owner = this.selectedGithubUser?.login;
						const repo = this.selectedGithubRepository || data.name;
						repository_url = `https://github.com/${repo_owner}/${repo}`;
					}

					this.app = {
						name: data.name,
						title: data.title,
						repository_url,
						github_installation_id: this.selectedGithubUser?.id,
						branch: this.selectedBranch.value,
					};
				},
				onError() {
					this.appValidated = false;
				},
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
							value: data[0].name,
						};
				},
			};
		},
	},
	computed: {
		appOwner() {
			if (this.tabIndex === 0) {
				const urlParts = this.githubAppLink.split('/');
				if (urlParts.length < 4) return;

				return urlParts[3];
			}
		},
		appName() {
			if (this.tabIndex === 0) {
				const urlParts = this.githubAppLink.split('/');
				if (urlParts.length < 5) return;

				return urlParts[4].replace('.git', '');
			}
		},
		branchOptions() {
			return (this.$resources.branches.data || []).map((branch) => ({
				label: branch.name,
				value: branch.name,
			}));
		},
		isAppOnBench() {
			if (!this.app) {
				return false;
			}

			for (const app of this.group.apps) {
				if (app.app == this.app.name) return true;
			}

			return false;
		},
	},
	methods: {
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
		addAppHandler() {
			this.$emit('app-added', this.app, this.isAppOnBench);
			this.show = false;
		},
	},
};
</script>
