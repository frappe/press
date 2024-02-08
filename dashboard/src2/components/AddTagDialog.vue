<template>
	<Dialog
		:options="{
			title: 'Add tag',
			actions: [
				{
					label: 'Add',
					variant: 'solid',
					onClick: () =>
						addNewTag(
							selectedTag?.value === '__new__' ? newTag : selectedTag.value
						)
				}
			]
		}"
		v-model="show"
	>
		<template #body-content>
			<FormControl
				v-if="selectedTag?.value !== '__new__'"
				label="Select tag"
				type="autocomplete"
				v-model="selectedTag"
				:options="tagOptions"
			/>
			<FormControl
				v-if="selectedTag?.value === '__new__'"
				v-model="newTag"
				label="Enter new tag and press enter"
				placeholder="production, staging, testing"
				@keydown.enter="e => addNewTag(e.target.value)"
			/>
		</template>
	</Dialog>
</template>
<script>
import {
	Autocomplete,
	Dialog,
	FormControl,
	getCachedDocumentResource
} from 'frappe-ui';

export default {
	name: 'AddTagDialog',
	props: ['doctype', 'docname'],
	emits: ['added', 'removed'],
	components: { Dialog, Autocomplete, FormControl },
	data() {
		return {
			selectedTag: null,
			newTag: '',
			show: true
		};
	},
	resources: {
		existingTags() {
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
	methods: {
		addNewTag(value) {
			if (!value) return;
			let $doc = getCachedDocumentResource(this.doctype, this.docname);
			if (!$doc) return;
			return $doc.addTag.submit({ tag: value }).then(() => {
				this.$emit('added', value);
				this.show = false;
			});
		}
	},
	computed: {
		tagOptions() {
			return [
				{ label: 'Create new tag', value: '__new__' },
				...(this.$resources.existingTags.data || []).map(d => ({
					label: d.tag,
					value: d.tag
				}))
			];
		}
	}
};
</script>
