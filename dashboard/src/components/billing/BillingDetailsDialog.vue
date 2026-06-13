<template>
	<Dialog v-model="show" title="Billing Details">
		<div
			v-if="showMessage"
			class="mb-5 inline-flex gap-1.5 text-base text-ink-gray-7"
		>
			<span class="lucide-info h-4" />
			<span> Add billing details to your account before proceeding.</span>
		</div>
		<BillingDetails
			ref="billingRef"
			@success="
				() => {
					show = false;
					emit('success');
				}
			"
		/>
	</Dialog>
</template>
<script setup>
import BillingDetails from './BillingDetails.vue'
import { Dialog } from 'frappe-ui'
import { ref } from 'vue'

const props = defineProps({
	showMessage: {
		type: Boolean,
		default: false,
	},
})
const emit = defineEmits(['success'])
const show = defineModel()
const billingRef = ref(null)
</script>
