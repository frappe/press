<template>
	<Dropdown v-if="dropdownProps" v-bind="dropdownProps">
		<ActionButton v-bind="dropdownProps.button" />
	</Dropdown>
	<Button v-if="buttonProps" v-bind="buttonProps">
		<template
			v-for="(slot, slotName) in buttonProps.slots"
			v-slot:[slotName]="slotProps"
		>
			<component :is="slot" v-bind="slotProps" />
		</template>
	</Button>
</template>

<script>
import { Button, Dropdown } from 'frappe-ui';
import { icon } from '../utils/components';

export default {
	name: 'ActionButton',
	components: {
		Button,
		Dropdown,
	},
	computed: {
		buttonProps() {
			if (
				this.$attrs.label &&
				!this.$attrs.options &&
				this.allowed(this.$attrs.label)
			) {
				return this.$attrs;
			}
		},
		dropdownProps() {
			if (
				this.$attrs.condition &&
				!this.$attrs.condition(this.$attrs.context)
			) {
				return;
			}

			const options = this.$attrs.options?.filter((option) =>
				this.allowed(option.label),
			);

			if (options?.length) {
				return {
					button: {
						label: 'Options',
						variant: 'ghost',
						slots: {
							icon: icon('more-horizontal'),
						},
					},
					...this.$attrs,
					label: this.$attrs.label,
					options,
				};
			}
		},
	},
	methods: {
		allowed(action) {
			if (this.$attrs.actionsAccess && action in this.$attrs.actionsAccess) {
				return this.$attrs.actionsAccess[action];
			} else {
				return true;
			}
		},
	},
};
</script>
