<template>
	<div class="px-5 py-4 border rounded-md space-y-12">
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
				<Button
					:variant="editing ? 'solid' : 'subtle'"
					@click="$resources.updateListing.submit()"
					>Save</Button
				>
			</div>
			<div class="grid grid-cols-1 md:grid-cols-2 gap-x-5 border-b py-6">
				<div class="border-r pr-6">
					<span class="font-medium text-base">Profile</span>
					<div class="my-4 group relative flex">
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
								method: 'press.api.marketplace.update_app_image'
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
					<div class="sm:col-span-4 pb-8">
						<FormControl
							class="mt-4"
							label="Title"
							type="text"
							@input="editing = true"
							v-model="marketplaceApp.title"
						/>
					</div>
					<div class="sm:col-span-4">
						<span class="font-medium text-base">Links</span>
						<div>
							<FormControl
								class="mt-4"
								label="Documentation"
								type="text"
								@input="editing = true"
								v-model="marketplaceApp.documentation"
							/>
							<FormControl
								class="mt-4"
								label="Website"
								type="text"
								@input="editing = true"
								v-model="marketplaceApp.website"
							/>
							<FormControl
								class="mt-4"
								label="Support"
								type="text"
								@input="editing = true"
								v-model="marketplaceApp.support"
							/>
							<FormControl
								class="mt-4"
								label="Terms of Service"
								type="text"
								@input="editing = true"
								v-model="marketplaceApp.terms_of_service"
							/>
							<FormControl
								class="mt-4"
								label="Privacy Policy"
								type="text"
								@input="editing = true"
								v-model="marketplaceApp.privacy_policy"
							/>
						</div>
					</div>
				</div>
				<div class="hidden md:block">
					<div class="flex w-full">
						<span class="font-medium text-base">Screenshots and Videos</span>
						<FileUploader
							class="ml-auto"
							@success="() => imageAddSuccess('Added screenshot')"
							@failure="imageAddFailure"
							fileTypes="image/*"
							:upload-args="{
								doctype: 'Marketplace App',
								docname: app.name,
								method: 'press.api.marketplace.add_app_screenshot'
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
						class="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-x-4 gap-y-4 pt-4"
					>
						<Dropdown
							class="w-fit"
							v-for="(image, index) in marketplaceApp.screenshots"
							:options="dropdownOptions(image)"
							right
						>
							<template v-slot="{ open }">
								<img
									class="mx-1 cursor-pointer w-36 h-24 overflow-x-auto object-cover rounded-md"
									:src="image"
								/>
							</template>
						</Dropdown>
					</div>
				</div>
			</div>
			<div class="mt-6">
				<span class="font-medium text-base">Summary</span>
				<FormControl
					class="mt-4"
					label="Description"
					type="textarea"
					@input="editing = true"
					v-model="marketplaceApp.description"
				/>
				<div class="mt-4">
					<span class="text-gray-600 text-xs">Description</span>
					<TextEditor
						class="mt-1 text-base rounded py-1.5 px-2 border border-gray-100 bg-gray-100 placeholder-gray-500 hover:border-gray-200 hover:bg-gray-200 focus:bg-white focus:border-gray-500 focus:shadow-sm focus:ring-0 focus-visible:ring-2 focus-visible:ring-gray-400 text-gray-800 transition-colors w-full block"
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

export default {
	name: 'MarketplaceAppOverview',
	props: ['app'],
	components: {
		FileUploader,
		TextEditor
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
				long_description: ''
			}
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
						args: this.marketplaceApp
					};
				},
				onSuccess(response) {
					toast.success('Updated Successfully');
					this.editing = false;
				}
			};
		},
		listingData() {
			return {
				url: 'press.api.client.run_doc_method',
				makeParams() {
					return {
						dt: 'Marketplace App',
						dn: this.app.doc.name,
						method: 'listing_details'
					};
				},
				auto: true,
				onSuccess(response) {
					this.marketplaceApp = { ...this.marketplaceApp, ...response.message };
				},
				onError(e) {
					toast.error(e);
				}
			};
		},
		removeScreenshot() {
			return {
				url: 'press.api.marketplace.remove_app_screenshot',
				onSuccess(response) {
					toast.success('Removed screenshot');
					this.$resources.listingData.reload();
				},
				onError(e) {
					toast.error(e);
				}
			};
		}
	},
	methods: {
		imageAddSuccess(message) {
			this.$resources.listingData.reload();
			toast.success(message);
		},
		imageAddFailure(e) {
			toast.error(e);
		},
		dropdownOptions(image) {
			return [
				{ label: 'View', onClick: () => window.open(image) },
				{
					label: 'Delete',
					onClick: () => {
						this.$resources.removeScreenshot.submit({
							name: this.app.doc.name,
							file: image
						});
					}
				}
			];
		}
	},
	computed: {
		profileImageUrl() {
			return this.app.doc.image;
		}
	}
};
</script>
