<template>
	<Card title="App Profile" subtitle="Your app's primary profile">
		<div class="flex items-center">
			<div class="group relative">
				<Avatar
					size="lg"
					shape="square"
					:label="app.title"
					:imageURL="profileImageUrl"
				/>
				<FileUploader
					@success="onAppImageChange"
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
				<p class="text-sm text-gray-600">{{ app.category }}</p>
			</div>
			<div class="ml-auto">
				<Button icon-left="edit" @click="showAppProfileEditDialog = true">
					Edit
				</Button>
			</div>
		</div>
		<div class="mt-5">
			<p class="text-lg font-semibold">Published Versions</p>
		</div>
		<div class="divide-y" v-if="app">
			<ListItem
				v-for="source in app.sources"
				:key="source.version"
				:title="source.version"
				:description="branchUri(source.source_information)"
			>
				<template #actions>
					<Badge :status="source.source_information.status" />
				</template>
			</ListItem>
		</div>

		<Dialog title="Update App Profile" v-model="showAppProfileEditDialog">
			<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
				<Input label="App Title" type="text" v-model="app.title" />
				<div>
					<span class="mb-2 block text-sm leading-4 text-gray-700">
						Category
					</span>
					<select class="form-select block w-full" v-model="app.category">
						<option v-for="category in categories" :key="category">
							{{ category }}
						</option>
					</select>
				</div>
			</div>

			<ErrorMessage class="mt-4" :error="$resources.updateAppProfile.error" />

			<template #actions>
				<div class="space-x-2">
					<Button @click="showAppProfileEditDialog = false">Cancel</Button>
					<Button
						type="primary"
						:loading="$resources.updateAppProfile.loading"
						loadingText="Saving..."
						@click="$resources.updateAppProfile.submit()"
					>
						Save changes
					</Button>
				</div>
			</template>
		</Dialog>
	</Card>
</template>

<script>
import FileUploader from '@/components/FileUploader.vue';

export default {
	name: 'MarketplaceAppProfile',
	props: {
		app: Object
	},
	components: {
		FileUploader
	},
	resources: {
		categories() {
			return {
				method: 'press.api.marketplace.categories',
				auto: true
			};
		},
		updateAppProfile() {
			let { name, title, category } = this.app;

			return {
				method: 'press.api.marketplace.update_app_profile',
				params: {
					name,
					title,
					category
				},
				onSuccess() {
					this.showAppProfileEditDialog = false;
					this.$resources.updateAppProfile.reset();
					this.notifySuccess();
				}
			};
		},
		profileImageUrl() {
			return {
				method: 'press.api.marketplace.profile_image_url',
				params: {
					app: this.app.name
				}
			};
		}
	},
	methods: {
		onAppImageChange() {
			this.$resources.profileImageUrl.submit();
			this.notifySuccess();
		},
		branchUri(source) {
			return `${source.repository_owner}/${source.repository}:${source.branch}`;
		},
		notifySuccess() {
			this.$notify({
				title: 'App Profile Updated!',
				icon: 'check',
				color: 'green'
			});
		}
	},
	data() {
		return {
			showAppProfileEditDialog: false
		};
	},
	computed: {
		categories() {
			if (
				this.$resources.categories.loading ||
				!this.$resources.categories.data
			) {
				return [];
			}

			return this.$resources.categories.data;
		},
		profileImageUrl() {
			if (!this.$resources.profileImageUrl.data) {
				return this.app.image;
			}

			return this.$resources.profileImageUrl.data;
		}
	}
};
</script>
