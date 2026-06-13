<template>
	<Dialog v-model="show" title="Add new card">
		<div
			v-if="showMessage"
			class="mb-5 inline-flex gap-1.5 text-base text-ink-gray-7"
		>
			<span class="lucide-info h-4" />
			<span> Add at least one card before changing the payment mode. </span>
		</div>
		<CardForm
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
import CardForm from './CardForm.vue'
import { Dialog } from 'frappe-ui'

const props = defineProps({
	showMessage: {
		type: Boolean,
		default: false,
	},
})

const emit = defineEmits(['success'])
const show = defineModel()
</script>
