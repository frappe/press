<template>
	<Button v-if="buttonProps" v-bind="buttonProps">
		<template
			v-for="(slot, slotName) in buttonProps.slots"
			v-slot:[slotName]="slotProps"
		>
			<component :is="slot" v-bind="slotProps" />
		</template>
	</Button>
	<Dropdown v-else-if="dropdownProps" v-bind="dropdownProps">
		<ActionButton v-bind="dropdownProps.button" />
	</Dropdown>
</template>
<script>
import { Button, Dropdown } from 'frappe-ui';
import { icon } from '../utils/components';

export default {
	name: 'ActionButton',
	components: {
		Button,
		Dropdown
	},
	computed: {
		buttonProps() {
			if (!this.$attrs.label || this.$attrs.options) return null;
			return this.$attrs;
		},

		dropdownProps() {
			if (!this.$attrs.options) return null;
			if (this.$attrs.condition) {
				if (!this.$attrs.condition(this.$attrs.context)) return null;
			}
			return {
				button: {
					label: 'Options',
					variant: 'ghost',
					slots: {
						icon: icon('more-horizontal')
					}
				},
				...this.$attrs,
				label: this.$attrs.label,
				options: this.$attrs.options
			};
		}
	}
};
</script>
