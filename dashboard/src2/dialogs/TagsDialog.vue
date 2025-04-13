<template>
	<Dialog v-model="showDialog" :options="{ title: 'Add Tag' }">
		<template #body-content>
			<div class="space-y-4">
				<div class="flex items-center space-x-2">
					<PressAutocomplete
						v-model="selectedTag"
						:options="tagOptions"
						label="Select or create a tag"
						:allowInputAsOption="true"
						class="w-full"
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
import Autocomplete from '../components/Autocomplete.vue';

export default {
	name: 'TagsDialog',
	props: ['docname', 'doctype'],
	components: { ErrorMessage, PressAutocomplete: Autocomplete },
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
				...(this.$resources.availableTags.data || [])
					.filter(t => !docTags.includes(t.tag))
					.map(t => ({
						label: t.tag || 'No label',
						value: t.tag
					}))
			];
		}
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
				error: 'Failed to add tag'
			});
		}
	}
};
</script>
