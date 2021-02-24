<template>
	<div class="grid grid-cols-1 gap-5 md:grid-cols-2">
		<AccountBillingUsage class="col-span-1 md:col-span-2" />
		<AccountBillingDetails />
		<AccountBillingCards />
		<AccountBillingPayments
			class="col-span-1 md:col-span-2"
			:invoice-name="invoiceName"
		/>
	</div>
</template>

<script>
import AccountBillingUsage from './AccountBillingUsage.vue';
import AccountBillingDetails from './AccountBillingDetails.vue';
import AccountBillingCards from './AccountBillingCards.vue';
import AccountBillingPayments from './AccountBillingPayments.vue';

export default {
	name: 'AccountBilling',
	props: ['invoiceName'],
	components: {
		AccountBillingUsage,
		AccountBillingDetails,
		AccountBillingCards,
		AccountBillingPayments
	}
};
</script>
