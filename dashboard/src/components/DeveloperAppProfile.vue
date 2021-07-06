<template>
	<Card title="App Profile" subtitle="Your app's primary profile">
		<div class="flex items-center">
			<div class="relative">
				<Avatar size="lg" :label="`${app.title} Logo`" :imageURL="app.image" />
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
				<p class="text-sm text-gray-600">{{ app.name }}</p>
			</div>
			<div class="ml-auto">
				<Button icon-left="edit" @click="showAppProfileEditDialog = true">
					Edit
				</Button>
			</div>
		</div>

		<Dialog title="Update App Profile" v-model="showAppProfileEditDialog">
			<div>
				<Input label="App Title" type="text" v-model="app.title" />
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
		updateAppProfile() {
			let { name, title } = this.app;

			return {
				method: 'press.api.developer.update_app_profile',
				params: {
					name,
					title
				},
				onSuccess() {
					this.showAppProfileEditDialog = false;
					this.$resources.updateAppProfile.reset();
					this.notifySuccess();
				}
			};
		}
	},
	methods: {
		onAppImageChange() {
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
	}
};
</script>
