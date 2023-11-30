<template>
	<Card title="App Profile" subtitle="Your app's primary profile">
		<div class="flex items-center border-b pb-6">
			<div class="group relative">
				<Avatar
					size="lg"
					shape="square"
					:label="app.title"
					:image="profileImageUrl"
				/>
				<FileUploader
					@success="onAppImageChange"
					@failure="onAppImageUploadError"
					fileTypes="image/*"
					:upload-args="{
						doctype: 'Marketplace App',
						docname: app.name,
						method: 'press.api.marketplace.update_app_image'
					}"
				>
					<template v-slot="{ openFileSelector, uploading, progress, error }">
						<div class="ml-4">
							<button
								@click="openFileSelector()"
								class="absolute inset-0 grid w-full place-items-center rounded-lg bg-black text-xs font-semibold text-white opacity-0 focus:opacity-50 focus:outline-none group-hover:opacity-50"
								:class="{ 'opacity-50': uploading }"
							>
								<span v-if="uploading">{{ progress }}%</span>
								<span v-else>Edit</span>
							</button>
							<button
								class="absolute bottom-0 left-0 grid w-full place-items-center rounded-md bg-gray-900 text-xs font-semibold text-white text-opacity-70 opacity-80 group-hover:opacity-0"
							>
								<span>Edit</span>
							</button>
						</div>
					</template>
				</FileUploader>
			</div>

			<div class="ml-4">
				<h3 class="text-lg font-semibold">
					{{ app.title }}
				</h3>
			</div>
			<div class="ml-auto">
				<Button icon-left="edit" @click="showAppProfileEditDialog = true">
					Edit
				</Button>
			</div>
		</div>
		<div class="mt-8 flex justify-between">
			<p class="text-lg font-semibold">Published Versions</p>
			<Button
				icon-left="plus"
				@click="
					() => {
						showCreateNewVersionDialog = true;
					}
				"
			>
				Add
			</Button>
		</div>
		<div class="divide-y" v-if="app">
			<ListItem
				v-for="source in app.sources"
				:key="source.version"
				:title="source.version"
				:description="branchUri(source.source_information)"
			>
				<template #actions>
					<div class="flex items-center">
						<Dropdown :options="dropdownItems(source)">
							<template v-slot="{ open }">
								<Button icon="more-horizontal" />
							</template>
						</Dropdown>
					</div>
				</template>
			</ListItem>
		</div>

		<Dialog
			:options="{
				title: 'Update App Title',
				actions: [
					{
						label: 'Save Changes',
						variant: 'solid',
						loading: $resources.updateAppTitle.loading,
						onClick: () => $resources.updateAppTitle.submit()
					}
				]
			}"
			v-model="showAppProfileEditDialog"
		>
			<template v-slot:body-content>
				<FormControl label="App Title" v-model="app.title" />

				<ErrorMessage class="mt-4" :message="$resources.updateAppTitle.error" />
			</template>
		</Dialog>

		<ChangeAppBranchDialog
			v-if="showBranchChangeDialog"
			:show="showBranchChangeDialog"
			:app="app"
			:source="selectedSource"
			:version="selectedVersion"
			:activeBranch="activeBranch"
			@close="showBranchChangeDialog = false"
		/>

		<CreateAppVersionDialog
			:show="showCreateNewVersionDialog"
			:app="app"
			@close="showCreateNewVersionDialog = false"
		/>
	</Card>
</template>

<script>
import CreateAppVersionDialog from '@/components/marketplace/CreateAppVersionDialog.vue';
import ChangeAppBranchDialog from '@/components/marketplace/ChangeAppBranchDialog.vue';
import FileUploader from '@/components/FileUploader.vue';
import { notify } from '@/utils/toast';

export default {
	name: 'MarketplaceAppProfile',
	props: {
		app: Object
	},
	components: {
		FileUploader,
		CreateAppVersionDialog,
		ChangeAppBranchDialog
	},
	data() {
		return {
			showAppProfileEditDialog: false,
			showAppVersionEditDialog: false,
			showBranchChangeDialog: false,
			showCreateNewVersionDialog: false,
			selectedSource: null,
			selectedVersion: null,
			activeBranch: null
		};
	},
	resources: {
		updateAppTitle() {
			let { name, title } = this.app;

			return {
				url: 'press.api.marketplace.update_app_title',
				params: {
					name,
					title
				},
				onSuccess() {
					this.showAppProfileEditDialog = false;
					this.$resources.updateAppTitle.reset();
					this.notifySuccess();
				}
			};
		},
		profileImageUrl() {
			return {
				url: 'press.api.marketplace.profile_image_url',
				params: {
					app: this.app.name
				}
			};
		},
		removeVersion() {
			return {
				url: 'press.api.marketplace.remove_version',
				onSuccess() {
					window.location.reload();
				},
				onError(e) {
					notify({
						title: e.messages.join('\n'),
						color: 'red',
						icon: 'x'
					});
				}
			};
		}
	},
	methods: {
		onAppImageChange() {
			this.$resources.profileImageUrl.submit();
			this.notifySuccess();
		},
		onAppImageUploadError(errorMessage) {
			notify({
				title: errorMessage,
				color: 'red',
				icon: 'x'
			});
		},
		branchUri(source) {
			return `${source.repository_owner}/${source.repository}:${source.branch}`;
		},
		dropdownItems(source) {
			return [
				{
					label: 'Change Branch',
					onClick: () => {
						this.selectedSource = source.source;
						this.selectedVersion = source.version;
						this.activeBranch = source.source_information.branch;
						this.showBranchChangeDialog = true;
					}
				},
				{
					label: 'Remove',
					onClick: () => {
						this.$resources.removeVersion.submit({
							name: this.app.name,
							version: source.version
						});
					}
				}
			];
		},
		notifySuccess() {
			notify({
				title: 'App Profile Updated!',
				icon: 'check',
				color: 'green'
			});
		}
	},
	computed: {
		profileImageUrl() {
			if (!this.$resources.profileImageUrl.data) {
				return this.app.image;
			}

			return this.$resources.profileImageUrl.data;
		}
	}
};
</script>
