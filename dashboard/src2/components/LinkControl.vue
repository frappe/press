<template>
	<FormControl
		v-bind="$attrs"
		type="autocomplete"
		:label="label"
		:options="autocompleteOptions"
		:modelValue="modelValue"
		@update:query="onQuery"
		@update:model-value="
			option => {
				if (option?.value) {
					$emit('update:modelValue', option.value);
				} else {
					$emit('update:modelValue', undefined);
				}
			}
		"
	/>
</template>
<script>
import { FormControl, debounce } from 'frappe-ui';

export default {
	name: 'LinkControl',
	props: ['label', 'options', 'modelValue'],
	emits: ['update:modelValue'],
	inheritAttrs: false,
	components: {
		FormControl
	},
	data() {
		return {
			query: '',
			currentValidValueInOptions: null
		};
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
					query: this.query
				},
				auto: true,
				transform: data => {
					return data.map(option => ({
						label: option.label || option.value,
						description: option.label ? option.value : undefined,
						value: option.value
					}));
				}
			};
		}
	},
	methods: {
		onQuery: debounce(function (query) {
			this.query = query.trim();
		}, 500)
	},
	computed: {
		autocompleteOptions() {
			let options = this.$resources.options.data || [];
			let currentValueInOptions = options.find(
				o => o.value === this.modelValue
			);

			if (currentValueInOptions) {
				this.currentValidValueInOptions = currentValueInOptions;
			}

			if (this.modelValue && !currentValueInOptions) {
				options = [this.currentValidValueInOptions, ...options];
			}
			return options;
		}
	}
};
</script>
