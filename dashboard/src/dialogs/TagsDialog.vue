<template>
	<Dialog v-model="showDialog" :options="{ title: 'Add Tag' }">
		<template #body-content>
			<div class="space-y-2">
				<FormControl
					type="checkbox"
					label="Create new tag"
					v-model="showNewTagInput"
				/>
				<div class="flex items-center space-x-2">
					<Combobox
						v-if="!showNewTagInput"
						v-model="selectedTag"
						:options="tagOptions"
						placeholder="Select an existing tag"
						class="w-full"
						open-on-focus
					/>
					<FormControl
						v-else
						v-model="selectedTag"
						type="text"
						placeholder="new-category"
						class="w-full"
					/>
					<Button
						label="Add"
						icon-left="plus"
						@click="addTag"
						:disabled="!selectedTag"
					/>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script>
import { Combobox, ErrorMessage, getCachedDocumentResource } from 'frappe-ui';
import { toast } from 'vue-sonner';

export default {
	name: 'TagsDialog',
	props: ['docname', 'doctype'],
	components: { ErrorMessage, Combobox },
	data() {
		return {
			showDialog: true,
			showNewTagInput: false,
			newTag: '',
			selectedTag: null,
		};
	},
	resources: {
		availableTags() {
			return {
				type: 'list',
				doctype: 'Press Tag',
				filters: { doctype_name: this.doctype },
				fields: ['tag'],
				pageLength: 1000,
				auto: true,
			};
		},
	},
	computed: {
		$doc() {
			return getCachedDocumentResource(this.doctype, this.docname);
		},
		tagOptions() {
			const docTags = this.$doc.doc.tags.map((t) => t.tag_name);
			return [
				...(this.$resources.availableTags.data || [])
					.filter((t) => !docTags.includes(t.tag))
					.map((t) => ({
						label: t.tag || 'No label',
						value: t.tag,
					})),
			];
		},
	},
	methods: {
		addTag() {
			const tag = this.selectedTag;
			toast.promise(this.$doc.addTag.submit({ tag }), {
				success: () => {
					this.selectedTag = null;
					return 'Tag added successfully';
				},
				loading: 'Adding tag...',
				error: 'Failed to add tag',
			});
		},
	},
	watch: {
		showNewTagInput() {
			this.selectedTag = null;
		},
	},
};
</script>
