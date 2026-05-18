<template>
	<AlertBanner :title="bannerMessage" type="warning">
		<a class="ml-auto" :href="stripeUrl" target="_blank">
			<Button variant="outline">Pay Now</Button>
		</a>
	</AlertBanner>
</template>
<script>
import AlertBanner from './AlertBanner.vue'

export default {
	name: 'AlertCardPaymentFailed',
	components: { AlertBanner },
	props: {
		errorMessage: {
			type: String,
			required: true,
		},
		stripeUrl: {
			type: String,
			required: true,
		},
	},
	computed: {
		bannerMessage() {
			return `Payment failed: ${this.errorMessage} Please settle the payment to avoid site suspension.`
		},
	},
}
</script>
