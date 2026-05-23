<template>
	<AlertBanner :title="budgetAlertMessage" type="warning"> </AlertBanner>
</template>
<script>
import AlertBanner from './AlertBanner.vue';
export default {
	name: 'AlertBudgetThreshold',
	components: { AlertBanner },
	props: {
		amount: {
			type: Number,
			required: true,
		},
		currency: {
			type: String,
		},
	},
	computed: {
		budgetAlertMessage() {
			return `Alerte budget : Votre coût Frappe Cloud a dépassé le seuil d'alerte du budget mensuel de <strong>${this.currency}${this.amount}</strong>`;
		},
	},
};
</script>
