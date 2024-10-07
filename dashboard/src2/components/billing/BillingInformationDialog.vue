<template>
	<Dialog :options="{ title: 'Add card to create sites' }" v-model="showDialog">
		<template v-slot:body-content>
			<StripeCard2
				class="mb-1"
				@complete="
					showDialog = false;
					$emit('success');
				"
			/>
		</template>
	</Dialog>
</template>
<script>
import StripeCard2 from '../StripeCard.vue';

export default {
	props: ['modelValue'],
	emits: ['update:modelValue', 'success'],
	components: {
		StripeCard2
	},
	computed: {
		showDialog: {
			get() {
				return this.modelValue;
			},
			set(value) {
				this.$emit('update:modelValue', value);
			}
		}
	}
};
</script>
