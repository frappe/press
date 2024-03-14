<template>
	<Autocomplete
		v-if="field.fieldtype == 'Autocomplete'"
		:options="autocompleteOptions"
		:placeholder="field.placeholder"
	/>
	<ListSelection
		v-else-if="field.fieldtype == 'ListSelection'"
		:options="field"
	/>
</template>
<script>
import { Autocomplete, FormControl } from 'frappe-ui';
import ListSelection from './ListSelection.vue';

export default {
	name: 'GenericDialogField',
	props: ['field'],
	components: { Autocomplete, FormControl, ListSelection },
	computed: {
		autocompleteOptions() {
			let options = [];
			if (this.field.fieldtype === 'Autocomplete') {
				if (this.field.options instanceof Array) {
					options = this.field.options;
				} else {
					options = this.field.options.data || [];
				}
			}
			return options.map(option => {
				if (typeof option === 'string') {
					return {
						label: option,
						value: option
					};
				}
				return option;
			});
		}
	}
};
</script>
