<template>
	<AlertBanner
		:title="`Your account currently has an outstanding balance of ${currency} ${amount}. Please settle the balance to avoid any site suspension.`"
		type="warning"
	>
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
			required: true
		},
		currency: {
			type: String
		}
	}
};
</script>
