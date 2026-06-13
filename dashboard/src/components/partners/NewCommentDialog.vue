<template>
	<Dialog v-model="show" title="New Comment" size="2xl">
		<div>
			<!-- New Comment -->
			<Editor
				v-model="content"
				placeholder="Write your comment here..."
				:editable="true"
				:extensions="extensions"
			>
				<EditorContent
					class="max-h-[50vh] overflow-y-auto border rounded-lg p-4 prose-sm max-w-none min-h-[4rem]"
				/>
				<div
					class="mt-2 flex flex-col justify-between sm:flex-row sm:items-center"
				>
					<EditorFixedMenu class="-ml-1 overflow-x-auto" :items="toolbar" />
					<div class="mt-2 flex items-center justify-end space-x-2 sm:mt-0">
						<Button variant="subtle" @click="emits('update:show', false)">
							Cancel
						</Button>
						<Button variant="solid" @click="saveComment()"> Submit </Button>
					</div>
				</div>
			</Editor>
		</div>
	</Dialog>
</template>
<script setup>
import { computed } from 'vue'
import {
	Editor,
	EditorContent,
	EditorFixedMenu,
	CommentKit,
	commentToolbar,
} from 'frappe-ui/editor'

const props = defineProps(['members'])
const content = defineModel('content')
const emits = defineEmits(['update:show', 'save-comment'])

const extensions = computed(() => [
	CommentKit.configure({
		heading: { levels: [2, 3, 4] },
		mention: { items: props.members },
	}),
])

const toolbar = commentToolbar

function saveComment() {
	emits('save-comment', content.value)
	emits('update:show', false)
}
</script>
