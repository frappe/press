<template>
	<Card title="Tags">
		<template #actions>
			<Dropdown :options="dropdownItems">
				<template v-slot="{ open }">
					<Button icon-right="chevron-down">Actions</Button>
				</template>
			</Dropdown>
		</template>
		<div class="divide-y">
			<ListItem v-for="tag in addedTags" :key="tag.name" :title="tag.tag">
				<template #actions>
					<Button icon="trash-2" @click="removeTag(tag.name)" />
				</template>
			</ListItem>
		</div>
	</Card>
	<Dialog :options="{ title: `Add a new tag` }" v-model="showAddDialog">
		<template v-slot:body-content>
			<ListItem v-for="tag in tags" :key="tag.name" :title="tag.tag">
				<template #actions>
					<Button icon="plus" @click="addTag(tag.name)" />
				</template>
			</ListItem>
		</template>
	</Dialog>
	<Dialog
		:options="{ title: `Create a new tag for ${doctype}` }"
		v-model="showNewDialog"
	>
		<template v-slot:body-content>
			<Input label="Enter Tag name" v-model="newTag" />
		</template>
		<template #actions>
			<Button @click="showNewDialog = false"> Cancel </Button>
			<Button appearance="primary" @click="$resources.createTag.submit()">
				Create
			</Button>
		</template>
	</Dialog>
</template>
<script>
export default {
	name: 'Tags',
	props: ['name', 'doctype', 'resourceTags', 'tags'],
	data() {
		return {
			dropdownItems: [
				{
					label: 'Add',
					handler: () => (this.showAddDialog = true)
				},
				{
					label: 'New',
					handler: () => (this.showNewDialog = true)
				}
			],
			showAddDialog: false,
			showNewDialog: false,
			newTag: '',
			addedTags: []
		};
	},
	resources: {
		addTag() {
			return {
				method: 'press.api.dashboard.add_tag',
				params: {
					name: this.name,
					doctype: this.doctype,
					tag: this.newTag
				},
				onSuccess(d) {
					this.addedTags.push(this.tags.find(t => t.name == d));
					this.showAddDialog = false;
					this.newTag = '';
				}
			};
		},
		removeTag() {
			return {
				method: 'press.api.dashboard.remove_tag',
				params: {
					name: this.name,
					doctype: this.doctype,
					tag: this.newTag
				},
				onSuccess(d) {
					this.addedTags = this.addedTags.filter(t => t.name != d);
					this.newTag = '';
				}
			};
		},
		createTag() {
			return {
				method: 'press.api.dashboard.create_new_tag',
				params: {
					name: this.name,
					doctype: this.doctype,
					tag: this.newTag
				},
				onSuccess(d) {
					this.addedTags.push({ name: d.name, tag: d.tag });
					this.showNewDialog = false;
					this.newTag = '';
				}
			};
		}
	},
	methods: {
		addTag(tagName) {
			this.newTag = tagName;
			this.$resources.addTag.submit();
		},
		removeTag(tagName) {
			this.newTag = tagName;
			this.$resources.removeTag.submit();
		}
	},
	mounted() {
		this.addedTags = this.resourceTags;
	}
};
</script>
