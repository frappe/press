<template>
	<Codemirror
		v-model="query"
		placeholder="Code goes here..."
		:style="{ height: '280px' }"
		:autofocus="true"
		:indent-with-tab="true"
		:tab-size="2"
		:extensions="extensions"
		@ready="handleReady"
	/>
</template>
<script>
import { MySQL, sql } from '@codemirror/lang-sql';
import { autocompletion } from '@codemirror/autocomplete';
import { Codemirror } from 'vue-codemirror';
import { shallowRef } from 'vue';

export default {
	name: 'SQLCodeEditor',
	components: {
		Codemirror,
	},
	props: ['schema'],
	emits: ['update:query', 'codeSelected', 'codeUnselected'],
	computed: {
		query: {
			get() {
				return this.$props.query;
			},
			set(value) {
				this.$emit('update:query', value);
			},
		},
		extensions() {
			if (!this.schema) {
				return [
					sql({
						dialect: MySQL,
						upperCaseKeywords: true,
					}),
					autocompletion({
						activateOnTyping: true,
						closeOnBlur: false,
						maxRenderedOptions: 10,
						icons: false,
					}),
				];
			}
			return [
				sql({
					dialect: MySQL,
					upperCaseKeywords: true,
					schema: this.schema,
				}),
				autocompletion({
					activateOnTyping: true,
					closeOnBlur: false,
					maxRenderedOptions: 10,
					icons: false,
				}),
			];
		},
	},
	setup(props, { emit }) {
		// Codemirror EditorView instance ref
		const view = shallowRef();
		const handleReady = (payload) => {
			view.value = payload.view;
			view.value.dom.addEventListener('mouseup', handleSelectionChange);
		};

		const handleSelectionChange = () => {
			if (!view.value) return;

			const { state } = view.value;
			const selection = state.selection.main;

			// Get the selected text
			if (!selection.empty) {
				const selectedText = state.doc.sliceString(
					selection.from,
					selection.to,
				);
				if ((selectedText ?? '').trim() === '') {
					emit('codeUnselected');
					return;
				}
				emit('codeSelected', selectedText);
			} else {
				emit('codeUnselected');
			}
		};
		return {
			handleReady,
		};
	},
};
</script>
<style>
.cm-focused {
	outline: none !important;
}
</style>
