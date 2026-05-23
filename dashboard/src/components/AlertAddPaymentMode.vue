<template>
	<AlertBanner
		:title="
			title ?? 'Ajoutez un mode de paiement pour commencer à créer des sites, des benches et plus encore.'
		"
		:type="type ?? 'warning'"
	>
		<Button class="ml-auto" @click="addPaymentMode" variant="outline">
			Ajouter un mode de paiement
		</Button>
	</AlertBanner>
</template>
<script>
import AlertBanner from './AlertBanner.vue';

export default {
	name: 'AlertAddPaymentMode',
	props: {
		title: String,
		type: String,
	},
	components: { AlertBanner },
	methods: {
		addPaymentMode() {
			this.$team.reload();

			this.$router.push({
				name: 'BillingOverview',
			});
		},
	},
};
</script>
