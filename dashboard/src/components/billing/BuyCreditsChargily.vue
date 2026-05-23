<template>
	<div class="space-y-4">
		<div>
			<label class="text-sm text-ink-gray-7 mb-2 block">Methode de paiement</label>
			<div class="grid grid-cols-2 gap-3">
				<button
					v-for="method in paymentMethods"
					:key="method.value"
					@click="selectedMethod = method.value"
					:class="[
						selectedMethod === method.value
							? 'border-gray-900 ring-1 ring-gray-900'
							: 'border-gray-300 hover:bg-gray-50',
						'flex items-center justify-center rounded border p-3 text-sm font-medium cursor-pointer'
					]"
				>
					{{ method.label }}
				</button>
			</div>
		</div>

		<ErrorMessage :message="errorMessage" />

		<div class="mt-8">
			<Button
				class="w-full"
				size="md"
				variant="solid"
				:label="
					loading
						? 'Redirection vers Chargily...'
						: `Payer ${amount ? amount + ' DZD' : ''} via Chargily`
				"
				:loading="loading"
				@click="createCheckout"
			/>
		</div>
	</div>
</template>
<script setup>
import { Button, ErrorMessage, createResource } from 'frappe-ui';
import { ref, inject } from 'vue';
import { DashboardError } from '../../utils/error';

const props = defineProps({
	amount: {
		type: Number,
		default: 0,
	},
	minimumAmount: {
		type: Number,
		default: 100,
	},
});

const emit = defineEmits(['success']);

const team = inject('team');

const selectedMethod = ref('edahabia');
const errorMessage = ref(null);
const loading = ref(false);

const paymentMethods = [
	{ label: 'EDAHABIA (Algerie Poste)', value: 'edahabia' },
	{ label: 'CIB (SATIM)', value: 'cib' },
];

const createChargilyCheckout = createResource({
	url: 'press.api.billing.create_chargily_checkout',
	onSuccess(data) {
		loading.value = false;
		errorMessage.value = null;
		if (data.checkout_url) {
			window.open(data.checkout_url, '_blank');
			emit('success');
		} else {
			errorMessage.value =
				"Impossible de creer la session de paiement. Veuillez reessayer.";
		}
	},
	onError(error) {
		loading.value = false;
		errorMessage.value =
			error.messages?.length
				? error.messages.join('\n')
				: error.message || "Une erreur s'est produite. Veuillez reessayer.";
	},
});

function createCheckout() {
	errorMessage.value = null;

	if (!props.amount || props.amount < props.minimumAmount) {
		errorMessage.value = `Le montant doit etre superieur ou egal a ${props.minimumAmount} DZD`;
		return;
	}

	if (!selectedMethod.value) {
		errorMessage.value = 'Veuillez selectionner une methode de paiement';
		return;
	}

	loading.value = true;
	createChargilyCheckout.submit({
		amount: props.amount,
		payment_method: selectedMethod.value,
	});
}
</script>
