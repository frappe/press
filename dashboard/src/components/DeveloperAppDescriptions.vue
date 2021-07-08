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
				>
					<div class="grid grid-cols-1 gap-5 md:grid-cols-2">
						<Input
							:rows="30"
							type="textarea"
							v-model="app.long_description"
						></Input>
						<div class="prose" v-html="descriptionHTML"></div>
					</div>
				</Dialog>
			</div>
		</div>
	</Card>
</template>

<script>
import MarkdownIt from 'markdown-it';

export default {
	name: 'DeveloperAppDescriptions',
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
			return {
				method: 'press.api.developer.update_app_summary',
				params: {
					name: this.app.name,
					summary: this.app.description
				},
				onSuccess() {
					this.notifySuccess('App Summary Updated!');
					this.showEditSummaryDialog = false;
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
