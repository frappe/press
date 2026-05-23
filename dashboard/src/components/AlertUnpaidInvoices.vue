<template>
	<AlertBanner :title="outstandingBalanceMessage" type="warning">
		<Button class="ml-auto" route="/billing" variant="outline">
			Payer maintenant
		</Button>
	</AlertBanner>
</template>
<script>
import AlertBanner from './AlertBanner.vue';

export default {
	name: 'AlertUnpaidInvoices',
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
		outstandingBalanceMessage() {
			return `Votre compte a actuellement un solde impayé de ${this.$format.userCurrency(
				this.amount,
			)}. Veuillez régler le solde pour éviter toute suspension de site.`;
		},
	},
};
</script>
