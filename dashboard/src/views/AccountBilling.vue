<template>
	<div class="space-y-5">
		<Alert title="Account Setup" v-if="!$account.team.default_payment_method">
			You haven't added your billing information yet. Add it to start creating
			sites.
			<template #actions>
				<Button type="primary" route="/welcome">Add Billing Information</Button>
			</template>
		</Alert>
		<div class="grid grid-cols-1 gap-5 md:grid-cols-2">
			<AccountBillingUsage class="col-span-1 md:col-span-2" />
			<AccountBillingDetails />
			<AccountBillingCards />
			<AccountBillingPayments
				class="col-span-1 md:col-span-2"
				:invoice-name="invoiceName"
			/>
			<AccountBillingCreditBalance class="col-span-1 md:col-span-2" />
		</div>
	</div>
</template>

<script>
import AccountBillingUsage from './AccountBillingUsage.vue';
import AccountBillingDetails from './AccountBillingDetails.vue';
import AccountBillingCards from './AccountBillingCards.vue';
import AccountBillingPayments from './AccountBillingPayments.vue';
import AccountBillingCreditBalance from './AccountBillingCreditBalance.vue';

export default {
	name: 'AccountBilling',
	props: ['invoiceName'],
	components: {
		AccountBillingUsage,
		AccountBillingDetails,
		AccountBillingCards,
		AccountBillingPayments,
		AccountBillingCreditBalance
	}
};
</script>
