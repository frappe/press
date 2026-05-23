<template>
	<AlertBanner :title="bannerMessage" type="warning">
		<a class="ml-auto" :href="stripeUrl" target="_blank">
			<Button variant="outline">Payer maintenant</Button>
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
			return `Échec du paiement : ${this.errorMessage} Veuillez régler le paiement pour éviter la suspension du site.`
		},
	},
}
</script>
