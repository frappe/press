<template>
	<div>
		<AlertBanner
			title="Veuillez ajouter votre adresse de facturation pour compléter votre profil Frappe Cloud."
			type="warning"
		>
			<Button
				class="ml-auto"
				@click="showBillingDetailsDialog = true"
				variant="outline"
			>
				Mettre à jour l'adresse
			</Button>
		</AlertBanner>
		<UpdateBillingDetails
			v-model="showBillingDetailsDialog"
			@updated="showBillingDetailsDialog = false"
		/>
	</div>
</template>
<script>
import AlertBanner from './AlertBanner.vue';
import UpdateBillingDetails from './UpdateBillingDetails.vue';

export default {
	name: 'AlertAddressDetails',
	components: { AlertBanner, UpdateBillingDetails },
	data() {
		return {
			showBillingDetailsDialog: false,
		};
	},
};
</script>
