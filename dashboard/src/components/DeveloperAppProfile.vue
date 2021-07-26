<template>
	<Card title="App Profile" subtitle="Your app's primary profile">
		<div class="flex items-center">
			<div class="relative">
				<Avatar
					size="lg"
					:label="`${app.title} Logo`"
					:imageURL="profileImageUrl"
				/>
				<FileUploader
					@success="onAppImageChange"
					fileTypes="image/*"
					:upload-args="{
						doctype: 'Marketplace App',
						docname: app.name,
						method: 'press.api.developer.update_app_image'
					}"
				>
					<template v-slot="{ openFileSelector, uploading, progress, error }">
						<div class="ml-4">
							<button
								@click="openFileSelector()"
								class="absolute inset-0 grid w-full text-xs font-semibold text-white bg-black rounded-full opacity-0 focus:outline-none focus:opacity-50 hover:opacity-50 place-items-center"
								:class="{ 'opacity-50': uploading }"
							>
								<span v-if="uploading">{{ progress }}%</span>
								<span v-else>Edit</span>
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
				v-for="version in publishedVersions"
				:key="version.version"
				:title="version.version"
				:description="
					`${version.repository_owner}/${version.repository}:${version.branch}`
				"
			/>
		</div>

		<Dialog title="Update App Profile" v-model="showAppProfileEditDialog">
			<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
				<Input label="App Title" type="text" v-model="app.title" />
				<div>
					<span class="block mb-2 text-sm leading-4 text-gray-700">
						Category
					</span>
					<select class="block w-full form-select" v-model="app.category">
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
	name: 'DeveloperAppProfile',
	props: {
		app: Object
	},
	components: {
		FileUploader
	},
	resources: {
		categories() {
			return {
				method: 'press.api.developer.categories',
				auto: true
			};
		},
		updateAppProfile() {
			let { name, title, category } = this.app;

			return {
				method: 'press.api.developer.update_app_profile',
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
		publishedVersions() {
			return {
				method: 'press.api.developer.published_versions',
				params: {
					name: this.app.name
				},
				auto: true
			};
		},
		profileImageUrl() {
			return {
				method: 'press.api.developer.profile_image_url',
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
		publishedVersions() {
			if (
				this.$resources.publishedVersions.loading ||
				!this.$resources.publishedVersions.data
			) {
				return [];
			}

			return this.$resources.publishedVersions.data;
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
