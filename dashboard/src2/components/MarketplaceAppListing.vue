<template>
	<div class="space-y-12 rounded-md border px-5 py-4">
		<div>
			<div class="flex justify-between border-b pb-4">
				<div>
					<h2 class="text-lg font-medium text-gray-900">App Profile</h2>
					<p class="mt-1 text-sm leading-6 text-gray-600">
						This information will be displayed publicly on the marketplace. Make
						sure you enter correct information without any broken links and
						images.
					</p>
				</div>
				<Button :variant="editing ? 'solid' : 'subtle'" @click="updateListing"
					>Save</Button
				>
			</div>
			<div class="grid grid-cols-1 gap-x-5 border-b py-6 md:grid-cols-2">
				<div class="border-r pr-6">
					<span class="text-base font-medium">Profile</span>
					<div class="group relative my-4 flex">
						<div class="flex flex-col">
							<Avatar
								size="3xl"
								shape="square"
								:label="app.doc.title"
								:image="profileImageUrl"
							/>
						</div>
						<FileUploader
							@success="() => imageAddSuccess('Profile photo updated')"
							@failure="imageAddFailure"
							fileTypes="image/*"
							:upload-args="{
								doctype: 'Marketplace App',
								docname: app.doc.name,
								method: 'press.api.marketplace.update_app_image',
							}"
						>
							<template
								v-slot="{ openFileSelector, uploading, progress, error }"
							>
								<div class="ml-4">
									<button
										@click="openFileSelector()"
										class="absolute inset-0 grid w-11.5 place-items-center rounded-lg bg-black text-xs font-medium text-white opacity-0 transition hover:opacity-50 focus:opacity-50 focus:outline-none"
										:class="{ 'opacity-50': uploading }"
									>
										<span v-if="uploading">{{ progress }}%</span>
										<span v-else>Edit</span>
									</button>
								</div>
							</template>
						</FileUploader>
					</div>
					<div class="pb-8 sm:col-span-4">
						<FormControl
							class="mt-4"
							label="Title"
							type="text"
							@input="editing = true"
							v-model="marketplaceApp.title"
						/>
					</div>
					<div class="sm:col-span-4">
						<span class="text-base font-medium">Links</span>
						<div>
							<FormControl
								class="mt-4"
								label="Documentation"
								type="text"
								@blur="validateLink('documentation')"
								@input="editing = true"
								v-model="marketplaceApp.documentation"
							/>
							<FormControl
								class="mt-4"
								label="Website"
								type="text"
								@blur="validateLink('website')"
								@input="editing = true"
								v-model="marketplaceApp.website"
							/>
							<FormControl
								class="mt-4"
								label="Support"
								type="text"
								@blur="validateLink('support')"
								@input="editing = true"
								v-model="marketplaceApp.support"
							/>
							<FormControl
								class="mt-4"
								label="Terms of Service"
								type="text"
								@blur="validateLink('terms_of_service')"
								@input="editing = true"
								v-model="marketplaceApp.terms_of_service"
							/>
							<FormControl
								class="mt-4"
								label="Privacy Policy"
								type="text"
								@blur="validateLink('privacy_policy')"
								@input="editing = true"
								v-model="marketplaceApp.privacy_policy"
							/>
						</div>
					</div>
				</div>
				<div class="hidden md:block">
					<div class="flex w-full">
						<span class="text-base font-medium">Screenshots and Videos</span>
						<FileUploader
							class="ml-auto"
							@success="() => imageAddSuccess('Added screenshot')"
							@failure="imageAddFailure"
							fileTypes="image/*"
							:upload-args="{
								doctype: 'Marketplace App',
								docname: app.name,
								method: 'press.api.marketplace.add_app_screenshot',
							}"
						>
							<template
								v-slot="{ openFileSelector, uploading, progress, error }"
							>
								<Button
									:loading="uploading"
									@click="openFileSelector()"
									icon-left="plus"
									label="Add"
								>
								</Button>
							</template>
						</FileUploader>
					</div>
					<div
						class="grid grid-cols-2 gap-x-4 gap-y-4 pt-4 lg:grid-cols-3 xl:grid-cols-4"
					>
						<Dropdown
							class="w-fit"
							v-for="(image, index) in marketplaceApp.screenshots"
							:options="dropdownOptions(image)"
							right
						>
							<template v-slot="{ open }">
								<img
									class="mx-1 h-24 w-36 cursor-pointer overflow-x-auto rounded-md object-cover"
									:src="image"
								/>
							</template>
						</Dropdown>
					</div>
				</div>
			</div>
			<div class="mt-6">
				<span class="text-base font-medium">Description</span>
				<FormControl
					class="mt-4"
					label="Summary"
					type="textarea"
					@input="editing = true"
					v-model="marketplaceApp.description"
				/>
				<div class="mt-4">
					<span class="text-xs text-gray-600">Description</span>
					<TextEditor
						class="mt-1 block w-full rounded border border-gray-100 bg-gray-100 px-2 py-1.5 text-base text-gray-800 placeholder-gray-500 transition-colors hover:border-gray-200 hover:bg-gray-200 focus:border-gray-500 focus:bg-white focus:shadow-sm focus:ring-0 focus-visible:ring-2 focus-visible:ring-gray-400"
						ref="textEditor"
						editor-class="rounded-b-lg max-w-[unset] prose-sm pb-[10vh]"
						:content="marketplaceApp.long_description"
						@change="marketplaceApp.long_description = $event"
						:editable="editable"
						:bubbleMenu="true"
					>
					</TextEditor>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
import { TextEditor } from 'frappe-ui';
import FileUploader from '@/components/FileUploader.vue';
import { toast } from 'vue-sonner';
import { getToastErrorMessage } from '../utils/toast';

export default {
	name: 'MarketplaceAppOverview',
	props: ['app'],
	components: {
		FileUploader,
		TextEditor,
	},
	data() {
		return {
			editing: false,
			editable: true,
			marketplaceApp: {
				title: this.app.doc.title,
				website: '',
				support: '',
				documentation: '',
				terms_of_service: '',
				privacy_policy: '',
				description: '',
				long_description: '',
			},
		};
	},
	resources: {
		updateListing() {
			return {
				url: 'press.api.client.run_doc_method',
				makeParams() {
					return {
						dt: 'Marketplace App',
						dn: this.app.doc.name,
						method: 'update_listing',
						args: this.marketplaceApp,
					};
				},
			};
		},
		listingData() {
			return {
				url: 'press.api.client.run_doc_method',
				makeParams() {
					return {
						dt: 'Marketplace App',
						dn: this.app.doc.name,
						method: 'listing_details',
					};
				},
				auto: true,
				onSuccess(response) {
					this.marketplaceApp = { ...this.marketplaceApp, ...response.message };
				},
				onError(e) {
					toast.error(getToastErrorMessage(e, 'Failed to fetch listing data'));
				},
			};
		},
		removeScreenshot() {
			return {
				url: 'press.api.marketplace.remove_app_screenshot',
			};
		},
	},
	methods: {
		imageAddSuccess(message) {
			this.$resources.listingData.reload();
			toast.success(message);
		},
		imageAddFailure(e) {
			toast.error(e);
		},
		updateListing() {
			toast.promise(this.$resources.updateListing.submit(), {
				success: () => {
					this.editing = false;
					return 'Updated successfully';
				},
				loading: 'Updating listing...',
				error: (err) => {
					return err.messages?.length
						? err.messages.join('\n')
						: err.message || 'Failed to update listing';
				},
			});
		},
		dropdownOptions(image) {
			return [
				{ label: 'View', onClick: () => window.open(image) },
				{
					label: 'Delete',
					onClick: () => {
						toast.promise(
							this.$resources.removeScreenshot.submit({
								name: this.app.doc.name,
								file: image,
							}),
							{
								loading: 'Deleting screenshot...',
								success: () => {
									this.$resources.listingData.reload();
									return 'Screenshot deleted successfully';
								},
								error: (err) => {
									return err.messages?.length
										? err.messages.join('\n')
										: err.message || 'Failed to delete screenshot';
								},
							},
						);
					},
				},
			];
		},
		validateLink(link) {
			const value = this.marketplaceApp[link] ?? '';

			// Regular expression to validate URL format
			const urlPattern =
				/^(https?:\/\/)?([\w\-]+\.)+[\w\-]{2,}(\/[\w\-._~:\/?#[\]@!$&'()*+,;=]*)?$/;

			// Check if the link is empty
			if (!value.trim()) {
				this.$toast.error(`${link.replace('_', ' ')} link is empty`);
				return false;
			}

			// Check if the link contains a valid URL
			if (!urlPattern.test(value.trim())) {
				this.$toast.error(`${link.replace('_', ' ')} contains an invalid URL`);
				return false;
			}
			return true;
		},
	},
	computed: {
		profileImageUrl() {
			return this.app.doc.image;
		},
	},
};
</script>
