<template>
	<Card title="Tags">
		<template #actions>
			<Button label="Add Tag" @click="showAddDialog = true" />
		</template>
		<div class="divide-y" v-if="addedTags?.length">
			<ListItem v-for="tag in addedTags" :key="tag.name" :title="tag.tag">
				<template #actions>
					<Button icon="x" @click="removeTag(tag.name)" />
				</template>
			</ListItem>
		</div>
		<div v-else class="m-4 text-center">
			<p class="text-base text-gray-500">No tags added yet</p>
		</div>
		<ErrorMessage
			:message="
				$resources.addTag.error ||
				$resources.createTag.error ||
				$resources.removeTag.error
			"
		/>
	</Card>
	<Dialog
		:options="{ title: `Add a New Tag for ${doctype}` }"
		v-model="showAddDialog"
	>
		<template #body-content>
			<Autocomplete
				placeholder="Tags"
				:options="getAutocompleteOptions"
				v-model="chosenTag"
				@update:modelValue="handleAutocompleteSelection"
			/>
			<FormControl
				v-if="showNewTagInput"
				v-model="newTag"
				class="mt-4"
				placeholder="Enter New Tag's name"
			/>
		</template>
		<template #actions>
			<Button variant="solid" class="w-full" @click="addTag()">{{
				showNewTagInput ? 'Create a New Tag' : 'Add Tag'
			}}</Button>
		</template>
	</Dialog>
</template>
<script>
export default {
	name: 'Tags',
	props: ['name', 'doctype', 'resourceTags', 'tags'],
	data() {
		return {
			showAddDialog: false,
			showNewTagInput: false,
			chosenTag: '',
			newTag: '',
			addedTags: [],
			createErrorMessage: ''
		};
	},
	resources: {
		addTag() {
			return {
				url: 'press.api.dashboard.add_tag',
				params: {
					name: this.name,
					doctype: this.doctype,
					tag: this.newTag
				},
				validate() {
					if (this.addedTags.find(t => t.name == this.newTag)) {
						return 'Tag already added';
					}
				},
				onSuccess(d) {
					this.addedTags.push(this.tags.find(t => t.name == d));
					this.showAddDialog = false;
					this.newTag = '';
					this.chosenTag = '';
				}
			};
		},
		removeTag() {
			return {
				url: 'press.api.dashboard.remove_tag',
				onSuccess(d) {
					this.addedTags = this.addedTags.filter(t => t.name != d);
				}
			};
		},
		createTag() {
			return {
				url: 'press.api.dashboard.create_new_tag',
				params: {
					name: this.name,
					doctype: this.doctype,
					tag: this.newTag
				},
				validate() {
					if (this.tags.find(t => t.tag === this.newTag)) {
						return 'Tag already exists';
					}
				},
				onSuccess(d) {
					this.addedTags.push({ name: d.name, tag: d.tag });
					this.showNewTagInput = false;
					this.newTag = '';
					this.chosenTag = '';
				}
			};
		}
	},
	methods: {
		addTag() {
			if (this.showNewTagInput) {
				this.$resources.createTag.submit();
			} else {
				this.$resources.addTag.submit();
			}
			this.showAddDialog = false;
		},
		removeTag(tagName) {
			this.$resources.removeTag.submit({
				name: this.name,
				doctype: this.doctype,
				tag: tagName
			});
		},
		handleAutocompleteSelection() {
			if (this.chosenTag.value === 'new_tag') {
				this.showNewTagInput = true;
			} else {
				this.newTag = this.chosenTag.value;
				this.showNewTagInput = false;
			}
		}
	},
	mounted() {
		this.addedTags = this.resourceTags;
	},
	computed: {
		getAutocompleteOptions() {
			return [
				{
					group: 'New Tag',
					items: [{ label: 'Create a New Tag', value: 'new_tag' }]
				},
				{
					group: 'Existing Tags',
					items: this.tags.map(t => ({ label: t.tag, value: t.name }))
				}
			];
		}
	}
};
</script>
