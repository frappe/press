<template>
	<div class="mt-8 flex-1">
		<div class="grid grid-cols-1 gap-5 md:grid-cols-2">
			<AccountBillingDetails class="row-span-1" />
			<AccountBillingCards class="row-span-1" />
			<AccountBillingPayments
				class="col-span-1 md:col-span-2"
				:invoice-name="invoiceName"
			/>
		</div>
	</div>
</template>

<script>
import AccountBillingDetails from '../billing/AccountBillingDetails.vue';
import AccountBillingCards from '../billing/AccountBillingCards.vue';
import AccountBillingPayments from '../billing/AccountBillingPayments.vue';

export default {
	name: 'SaasBilling',
	props: ['invoiceName'],
	components: {
		AccountBillingDetails,
		AccountBillingCards,
		AccountBillingPayments
	}
};
</script>
