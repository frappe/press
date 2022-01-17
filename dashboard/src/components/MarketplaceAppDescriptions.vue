<template>
	<Card
		class="md:col-span-2"
		title="App Descriptions"
		subtitle="Details about your app"
	>
		<div class="divide-y" v-if="app">
			<ListItem title="Summary" :description="app.description">
				<template #actions>
					<Button icon-left="edit" @click="showEditSummaryDialog = true">
						Edit
					</Button>
				</template>
			</ListItem>
			<Dialog title="Update App Summary" v-model="showEditSummaryDialog">
				<Input
					label="Summary of the app"
					type="textarea"
					v-model="app.description"
				/>
				<ErrorMessage class="mt-4" :error="$resources.updateAppSummary.error" />

				<template #actions>
					<div class="space-x-2">
						<Button @click="showEditSummaryDialog = false">Cancel</Button>
						<Button
							type="primary"
							:loading="$resources.updateAppSummary.loading"
							loadingText="Saving..."
							@click="$resources.updateAppSummary.submit()"
						>
							Save changes
						</Button>
					</div>
				</template>
			</Dialog>
			<div class="py-3">
				<ListItem title="Long Description">
					<template #actions>
						<Button icon-left="edit" @click="showEditDescriptionDialog = true">
							Edit
						</Button>
					</template>
				</ListItem>
				<div
					class="mt-1 prose text-gray-600"
					v-if="app.description"
					v-html="descriptionHTML"
				></div>
				<Dialog
					title="Update App Description"
					v-model="showEditDescriptionDialog"
					:dismissable="true"
					:width="full"
				>
					<div class="grid grid-cols-1 gap-5 md:grid-cols-2">
						<Input
							:rows="30"
							type="textarea"
							v-model="app.long_description"
						></Input>
						<div class="prose" v-html="descriptionHTML"></div>
					</div>

					<ErrorMessage
						class="mt-4"
						:error="$resources.updateAppDescription.error"
					/>

					<template #actions>
						<Button
							type="primary"
							:loading="$resources.updateAppDescription.loading"
							loadingText="Saving..."
							@click="$resources.updateAppDescription.submit()"
						>
							Save Changes
						</Button>
					</template>
				</Dialog>
			</div>
		</div>
	</Card>
</template>

<script>
import MarkdownIt from 'markdown-it';

export default {
	name: 'MarketplaceAppDescriptions',
	props: {
		app: Object
	},
	data() {
		return {
			showEditSummaryDialog: false,
			showEditDescriptionDialog: false
		};
	},
	resources: {
		updateAppSummary() {
			let { name, description } = this.app;
			return {
				method: 'press.api.marketplace.update_app_summary',
				params: {
					name,
					summary: description
				},
				onSuccess() {
					this.notifySuccess('App Summary Updated!');
					this.showEditSummaryDialog = false;
				}
			};
		},
		updateAppDescription() {
			let { name, long_description } = this.app;
			return {
				method: 'press.api.marketplace.update_app_description',
				params: {
					name,
					description: long_description
				},
				onSuccess() {
					this.notifySuccess('App Description Updated!');
					this.showEditDescriptionDialog = false;
				}
			};
		}
	},
	computed: {
		descriptionHTML() {
			if (this.app && this.app.long_description) {
				return MarkdownIt().render(this.app.long_description);
			}

			return '';
		}
	},
	methods: {
		notifySuccess(message) {
			this.$notify({
				title: message,
				icon: 'check',
				color: 'green'
			});
		}
	}
};
</script>
