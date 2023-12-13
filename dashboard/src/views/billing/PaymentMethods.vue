<template>
	<div class="space-y-5">
		<AccountBillingDetails />
		<AccountBillingCards />
	</div>
</template>

<script>
import AccountBillingDetails from './AccountBillingDetails.vue';
import AccountBillingCards from './AccountBillingCards.vue';

export default {
	name: 'BillingScreen',
	pageMeta() {
		return {
			title: 'Billing - Frappe Cloud'
		};
	},
	props: ['invoiceName'],
	components: {
		AccountBillingDetails,
		AccountBillingCards
	}
};
</script>
