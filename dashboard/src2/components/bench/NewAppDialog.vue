<template>
	<Dialog
		:options="{
			title: 'Add a New App to your Bench',
			size: 'xl'
		}"
		:modelValue="modelValue"
		@update:modelValue="$emit('update:modelValue', $event)"
	>
		<template #body-content>
			<FTabs :tabs="tabs" v-model="tabIndex" v-slot="{ tab }">
				<div class="mx-2 my-4">
					<div v-if="tab.value === 'public-github-app'" class="space-y-4">
						<div class="flex items-end space-x-2">
							<FormControl
								class="grow"
								label="Enter the app's GitHub url"
								v-model="githubAppLink"
							/>
							<Button
								v-if="!selectedBranch"
								label="Fetch Branches"
								:loading="$resources.branches.loading"
								@click="$resources.branches.submit()"
							/>
							<Autocomplete
								v-else
								:options="
									$resources.branches.data.map(b => ({
										label: b.name,
										value: b.name
									}))
								"
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
						<div v-if="appValidated" class="flex text-base text-gray-700">
							<GreenCheckIcon class="mr-2 w-4" />
							Found {{ this.app.title }} ({{ this.app.name }})
						</div>
						<div
							v-else-if="appValidated === false && selectedBranch"
							class="flex text-base text-gray-700"
						>
							<FeatherIcon name="x-circle" class="mr-2 w-4 text-red-700" />
							Not a valid Frappe app
						</div>
						<ErrorMessage
							:message="
								$resources.branches.error ||
								$resources.validateApp.error ||
								$resources.addApp.error
							"
						/>
					</div>
					<div v-else-if="tab.value === 'your-github-app'" class="space-y-4">
						<GetAppFromGithub @onSelect="d => (app = d)" />

						<ErrorMessage :message="$resources.addApp.error" />

						<Button
							v-if="app"
							:loading="$resources.addApp.loading"
							@click="$resources.addApp.submit()"
							>Add to bench</Button
						>
					</div>
				</div>
			</FTabs>
		</template>
		<template #actions>
			<Button
				class="w-full"
				label="Add App to bench"
				variant="solid"
				:disabled="!appValidated"
				:loading="$resources.addApp.loading"
				@click="$resources.addApp.submit()"
			/>
		</template>
	</Dialog>
</template>

<script>
import GetAppFromGithub from './GetAppFromGithub.vue';
import { Tabs } from 'frappe-ui';

export default {
	name: 'NewAppDialog',
	components: {
		GetAppFromGithub,
		FTabs: Tabs
	},
	props: ['benchName', 'modelValue'],
	emits: ['update:modelValue'],
	data() {
		return {
			app: null,
			tabIndex: 0,
			githubAppLink: '',
			selectedBranch: '',
			appValidated: null,
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
		githubAppLink() {
			this.selectedBranch = '';
			this.appValidated = null;
		}
	},
	resources: {
		appList() {
			return {
				type: 'list',
				doctype: 'Release Group App',
				cache: ['ObjectList', 'Release Group App', this.benchName],
				parent: 'Release Group',
				filters: {
					parenttype: 'Release Group',
					parent: this.benchName
				}
			};
		},
		validateApp() {
			let params = {
				owner: this.appOwner,
				repository: this.appName,
				branch: this.selectedBranch.value
			};
			return {
				url: 'press.api.github.app',
				params,
				onSuccess(data) {
					this.appValidated = true;
					if (data) {
						this.app = {
							name: data.name,
							title: data.title,
							repository_url: this.githubAppLink,
							branch: this.selectedBranch.value
						};
					}
				},
				onError() {
					this.appValidated = false;
				}
			};
		},
		branches() {
			let params = {
				owner: this.appOwner,
				name: this.appName
			};

			return {
				url: 'press.api.github.branches',
				params,
				onSuccess(branches) {
					this.selectedBranch = {
						label: branches[0].name,
						value: branches[0].name
					};

					this.$resources.validateApp.submit({
						owner: this.appOwner,
						repository: this.appName,
						branch: branches[0].name
					});
				},
				validate() {
					if (!this.githubAppLink) {
						return 'Please enter a valid github link';
					}
				}
			};
		},
		addApp() {
			return {
				url: 'press.api.app.new',
				params: {
					app: {
						name: this.app?.name,
						title: this.app?.title,
						repository_url: this.app?.repository_url,
						branch: this.app?.branch,
						github_installation_id: this.app?.github_installation_id,
						group: this.benchName
					}
				},
				onSuccess() {
					this.$resources.appList.reload();
					this.$emit('update:modelValue', false);
				}
			};
		}
	},
	computed: {
		appOwner() {
			return this.githubAppLink.split('/')[3];
		},
		appName() {
			return this.githubAppLink.split('/')[4];
		}
	}
};
</script>
