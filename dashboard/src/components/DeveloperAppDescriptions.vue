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
				<Dialog class="bg-gradient-blue" title="Update App Description" v-model="showEditDescriptionDialog">
					<div class="grid grid-cols-1 gap-5 md:grid-cols-2">
						<Input :rows="30" type="textarea" v-model="app.long_description"></Input>
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
	computed: {
		descriptionHTML() {
			if (this.app && this.app.long_description) {
				return MarkdownIt().render(this.app.long_description);
			}

			return '';
		}
	}
};
</script>
