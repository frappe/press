<template>
	<FormControl
		ref="formControl"
		v-bind="$attrs"
		type="combobox"
		:label="label"
		:options="autocompleteOptions"
		:modelValue="modelValue"
		:placeholder="placeholder"
		@update:modelValue="
			(optionValue) => {
				if (optionValue) {
					$emit('update:modelValue', optionValue);
				} else {
					$emit('update:modelValue', undefined);
				}
			}
		"
	/>
</template>
<script>
import { FormControl, debounce } from 'frappe-ui';
import { nextTick } from 'vue';

export default {
	name: 'LinkControl',
	props: ['label', 'options', 'modelValue', 'placeholder'],
	emits: ['update:modelValue'],
	inheritAttrs: false,
	components: {
		FormControl,
	},
	data() {
		return {
			query: '',
			currentValidValueInOptions: null,
		};
	},
	beforeUnmount() {
		const root = this.$refs.formControl?.$el;
		const input = root?.querySelector('input');

		if (!input) return;

		input.removeEventListener('input', this.onNativeInput);
	},
	mounted() {
		nextTick(() => {
			const root = this.$refs.formControl?.$el;
			if (!root) return;

			const input = root.querySelector('input');

			if (!input) return;
			input.addEventListener('input', this.onNativeInput);
		});
	},
	resources: {
		options() {
			return {
				url: 'press.api.client.search_link',
				params: {
					doctype: this.options.doctype,
					order_by: this.options.orderBy,
					page_length: this.options.pageLength || 10,
					filters: this.options.filters,
					query: this.query,
				},
				auto: true,
				initialData: this.options.initialData || [],
				transform: (data) => {
					return data.map((option) => ({
						label: option.label || option.value,
						description: option.label ? option.value : undefined,
						value: option.value,
					}));
				},
			};
		},
	},
	methods: {
		onQuery: debounce(function (query) {
			this.query = query.trim();
		}, 500),
		onNativeInput(e) {
			this.onQuery(e.target.value);
		},
	},
	computed: {
		autocompleteOptions() {
			let options = this.$resources.options.data || [];
			const currentValueInOptions = options.find(
				(o) => o.value === this.modelValue,
			);

			if (currentValueInOptions) {
				this.currentValidValueInOptions = currentValueInOptions;
			}

			if (
				this.modelValue &&
				!currentValueInOptions &&
				this.currentValidValueInOptions
			) {
				options = [this.currentValidValueInOptions, ...options];
			}

			return options;
		},
	},
};
</script>
