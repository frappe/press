<template>
	<Dialog v-model="showDialog" :options="{ title: 'Add Tag' }">
		<template #body-content>
			<div class="space-y-4">
				<div class="flex items-center space-x-2">
					<FormControl
						v-if="selectedTag?.value !== '__new__'"
						class="w-full"
						label="Select or create a tag"
						type="autocomplete"
						v-model="selectedTag"
						:options="tagOptions"
					/>
					<FormControl
						v-if="selectedTag?.value === '__new__'"
						class="w-full"
						v-model="newTag"
						label="Enter new tag"
						placeholder="production, staging, testing"
					/>
					<Button
						label="Add"
						icon-left="plus"
						@click="addTag"
						class="mt-5"
						:disabled="!selectedTag"
					/>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script>
import { ErrorMessage, getCachedDocumentResource } from 'frappe-ui';
import { toast } from 'vue-sonner';

export default {
	name: 'TagsDialog',
	props: ['docname', 'doctype'],
	components: { ErrorMessage },
	data() {
		return {
			showDialog: true,
			newTag: '',
			selectedTag: null
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
				auto: true
			};
		}
	},
	computed: {
		$doc() {
			return getCachedDocumentResource(this.doctype, this.docname);
		},
		tagOptions() {
			const docTags = this.$doc.doc.tags.map(t => t.tag_name);
			return [
				{ label: 'Create new tag', value: '__new__' },
				...(this.$resources.availableTags.data || [])
					.filter(t => !docTags.includes(t.tag))
					.map(t => ({
						label: t.tag,
						value: t.tag
					}))
			];
		}
	},
	methods: {
		addTag() {
			const tag =
				this.selectedTag?.value === '__new__'
					? this.newTag
					: this.selectedTag.value;
			toast.promise(this.$doc.addTag.submit({ tag }), {
				success: () => {
					this.selectedTag = null;
					return 'Tag added successfully';
				},
				loading: 'Adding tag...',
				error: 'Failed to add tag'
			});
		}
	}
};
</script>
