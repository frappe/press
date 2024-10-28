<template>
	<AlertBanner
		title="You have unpaid invoices. Please settle your outstanding invoices to avoid site suspension."
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
	components: { AlertBanner }
};
</script>
