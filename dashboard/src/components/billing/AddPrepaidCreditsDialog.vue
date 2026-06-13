<template>
	<Dialog v-model="show" title="Add Credit Balance">
		<div
			v-if="showMessage"
			class="mb-5 inline-flex gap-1.5 text-base text-ink-gray-7"
		>
			<span class="lucide-info h-4" />
			<span>
				Add credits to your account before changing the payment mode.
			</span>
		</div>
		<PrepaidCreditsForm
			:minimumAmount="minimumAmount"
			:type="type"
			:docName="docName"
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
import PrepaidCreditsForm from './PrepaidCreditsForm.vue'
import { Dialog } from 'frappe-ui'

const props = defineProps({
	showMessage: {
		type: Boolean,
		default: false,
	},
	minimumAmount: {
		type: Number,
		default: null,
	},
	docName: {
		type: String,
		default: null,
	},
	type: {
		type: String,
		default: 'Prepaid Credits',
	},
})

const emit = defineEmits(['success'])
const show = defineModel()
</script>
