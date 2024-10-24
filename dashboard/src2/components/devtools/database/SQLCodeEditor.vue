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
		Codemirror
	},
	props: ['schema'],
	emits: ['update:query'],
	computed: {
		query: {
			get() {
				return this.$props.query;
			},
			set(value) {
				this.$emit('update:query', value);
			}
		}
	},
	setup(props) {
		const extensions = [
			sql({
				dialect: MySQL,
				upperCaseKeywords: true,
				schema: props.schema
			}),
			autocompletion({
				activateOnTyping: true,
				closeOnBlur: false,
				maxRenderedOptions: 10,
				icons: false
			})
		];
		// Codemirror EditorView instance ref
		const view = shallowRef();
		const handleReady = payload => {
			view.value = payload.view;
		};
		return {
			extensions,
			handleReady
		};
	}
};
</script>
<style>
.cm-focused {
	outline: none !important;
}
</style>
