<template>
	<AlertBanner :title="outstandingBalanceMessage" type="warning">
		<Button class="ml-auto" route="/billing" variant="outline">
			Pay Now
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
			return `Your account currently has an outstanding balance of ${this.$format.userCurrency(
				this.amount,
			)}. Please settle the balance to avoid any site suspension.`;
		},
	},
};
</script>
