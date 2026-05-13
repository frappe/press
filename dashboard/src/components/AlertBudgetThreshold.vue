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
			return `Budget Alert: Your Frappe Cloud cost has exceeded the monthly budget alert threshold by <strong>${this.currency}${this.amount}</strong>`;
		},
	},
};
</script>
