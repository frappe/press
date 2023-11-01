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
			<Dialog
				:options="{
					title: 'Update App Summary',
					actions: [
						{
							label: 'Save Changes',
							variant: 'solid',
							loading: $resources.updateAppSummary.loading,
							onClick: () => $resources.updateAppSummary.submit()
						}
					]
				}"
				v-model="showEditSummaryDialog"
			>
				<template v-slot:body-content>
					<FormControl
						label="Summary of the app"
						type="textarea"
						v-model="app.description"
					/>
					<ErrorMessage
						class="mt-4"
						:message="$resources.updateAppSummary.error"
					/>
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
					class="prose mt-1 text-gray-600"
					v-if="app.description"
					v-html="descriptionHTML"
				></div>
				<Dialog
					:options="{
						title: 'Update App Description',
						size: '5xl',
						actions: [
							{
								label: 'Save Changes',
								variant: 'solid',
								loading: $resources.updateAppDescription.loading,
								onClick: () => $resources.updateAppDescription.submit()
							}
						]
					}"
					:dismissable="true"
					v-model="showEditDescriptionDialog"
					width="full"
				>
					<template v-slot:body-content>
						<div class="grid grid-cols-1 gap-5 md:grid-cols-2">
							<FormControl
								:rows="30"
								type="textarea"
								v-model="app.long_description"
							/>
							<div class="prose" v-html="descriptionHTML"></div>
						</div>

						<ErrorMessage
							class="mt-4"
							:message="$resources.updateAppDescription.error"
						/>
					</template>
				</Dialog>
			</div>
		</div>
		<template #actions>
			<Button
				:loading="$resources.fetchReadme.loading"
				@click="$resources.fetchReadme.submit()"
			>
				Fetch Readme
			</Button>
		</template>
	</Card>
</template>

<script>
import MarkdownIt from 'markdown-it';
import { notify } from '@/utils/toast';

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
				url: 'press.api.marketplace.update_app_summary',
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
				url: 'press.api.marketplace.update_app_description',
				params: {
					name,
					description: long_description
				},
				onSuccess() {
					this.notifySuccess('App Description Updated!');
					this.showEditDescriptionDialog = false;
				}
			};
		},
		fetchReadme() {
			return {
				url: 'press.api.marketplace.fetch_readme',
				params: { name: this.app.name },
				onSuccess() {
					notify({
						title: 'Successfully fetched latest readme',
						message: 'Long description updated!',
						icon: 'check',
						color: 'green'
					});
				},
				onError(e) {
					notify({
						title: e,
						color: 'red',
						icon: 'x'
					});
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
			notify({
				title: message,
				icon: 'check',
				color: 'green'
			});
		}
	}
};
</script>
