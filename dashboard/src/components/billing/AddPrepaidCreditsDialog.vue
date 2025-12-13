<template>
	<Dialog v-model="show" :options="{ title: 'Add Credit Balance' }">
		<template #body-content>
			<div
				v-if="showMessage"
				class="mb-5 inline-flex gap-1.5 text-base text-gray-700"
			>
				<FeatherIcon class="h-4" name="info" />
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
		</template>
	</Dialog>
</template>
<script setup>
import PrepaidCreditsForm from './PrepaidCreditsForm.vue';
import { Dialog, FeatherIcon } from 'frappe-ui';

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
});

const emit = defineEmits(['success']);
const show = defineModel();
</script>
