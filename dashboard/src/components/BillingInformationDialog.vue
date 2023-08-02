<template>
	<Dialog :options="{ title: 'Add card to create sites' }" v-model="showDialog">
		<template v-slot:body-content>
			<StripeCard
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
import StripeCard from '@/components/StripeCard.vue';

export default {
	name: 'BillingInformationDialog',
	props: ['modelValue'],
	emits: ['update:modelValue', 'success'],
	components: {
		StripeCard
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
