<template>
	<Dialog v-model="show" :options="{ title: 'New Comment', size: '2xl' }">
		<template #body-content>
			<div>
				<!-- New Comment -->
				<TextEditor
					editor-class="prose-sm max-w-none min-h-[4rem]"
					placeholder="Write your comment here..."
					ref="commentEditor"
					:content="content"
					:editable="true"
					:starterkit-options="{ heading: { levels: [2, 3, 4] } }"
					:mentions="members"
				>
					<template #editor="{ editor }">
						<TextEditorContent
							class="max-h-[50vh] overflow-y-auto border rounded-lg p-4"
							:editor="editor"
						/>
					</template>
					<template #bottom>
						<div
							class="mt-2 flex flex-col justify-between sm:flex-row sm:items-center"
						>
							<TextEditorFixedMenu
								class="-ml-1 overflow-x-auto"
								:buttons="[
									'Paragraph',
									['Heading 2', 'Heading 3', 'Heading 4'],
									'Separator',
									'Bold',
									'Italic',
									'Separator',
									'Bullet List',
									'Numbered List',
									'Separator',
									'Link',
									'Image',
								]"
							/>
							<div class="mt-2 flex items-center justify-end space-x-2 sm:mt-0">
								<Button variant="subtle" @click="emits('update:show', false)">
									Cancel
								</Button>
								<Button variant="solid" @click="saveComment()"> Submit </Button>
							</div>
						</div>
					</template>
				</TextEditor>
			</div>
		</template>
	</Dialog>
</template>
<script setup>
import { ref, computed, defineEmits, defineProps } from 'vue';
import { TextEditor, TextEditorFixedMenu, TextEditorContent } from 'frappe-ui';

const commentEditor = ref('');
const editor = computed(() => {
	return commentEditor.value.editor;
});

const props = defineProps(['members']);

const content = defineModel('content');
const emits = defineEmits(['update:show', 'save-comment']);
function saveComment() {
	const commentContent = editor.value.getHTML();
	emits('save-comment', commentContent);
	emits('update:show', false);
}
</script>
