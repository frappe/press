<template>
	<Card
		class="md:col-span-2"
		title="Screenshots"
		subtitle="Add screenshots to show on the marketplace website"
	>
		<div>
			<div class="flex flex-row">
				<Avatar
					size="lg"
					class="mx-1 cursor-pointer hover:bg-red-100 hover:opacity-20"
					shape="square"
					:imageURL="image.image"
					v-for="(image, index) in app.screenshots"
					@click="removeScreenshot(image.image, index)"
				>
				</Avatar>
				<FileUploader
					@success="onAppImageAdd"
					@failure="onAppImageUploadError"
					fileTypes="image/*"
					:upload-args="{
						doctype: 'Marketplace App',
						docname: app.name,
						method: 'press.api.marketplace.add_app_screenshot'
					}"
				>
					<template v-slot="{ openFileSelector, uploading, progress, error }">
						<Button
							class="ml-1 h-12 w-12"
							@click="openFileSelector()"
							icon="plus"
						>
						</Button>
					</template>
				</FileUploader>
			</div>
		</div>
	</Card>
</template>

<script>
import FileUploader from '@/components/FileUploader.vue';
import { notify } from '@/utils/toast';

export default {
	name: 'MarketplaceAppScreenshots',
	props: {
		app: Object
	},
	components: {
		FileUploader
	},
	methods: {
		onAppImageAdd(file) {
			this.app.screenshots.push({ image: file });
			notify({
				title: 'Screenshot was added successfully!',
				icon: 'check',
				color: 'green'
			});
		},
		removeScreenshot(file, index) {
			this.$resources.removeScreenshot.submit({
				name: this.app.name,
				file: file
			});
			this.app.screenshots.splice(index, 1);
		},
		onAppImageUploadError(errorMessage) {
			notify({
				title: errorMessage,
				color: 'red',
				icon: 'x'
			});
		}
	},
	resources: {
		removeScreenshot(file) {
			return {
				url: 'press.api.marketplace.remove_app_screenshot'
			};
		}
	}
};
</script>
