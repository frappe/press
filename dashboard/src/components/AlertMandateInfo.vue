<template>
	<div>
		<AlertBanner
			title="Due to RBI regulations, we need to generate a mandate to process payments from your card."
			type="warning"
		>
			<Button
				class="ml-auto shrink-0"
				@click="showAddCardDialog = true"
				variant="outline"
			>
				Update Card
			</Button>
		</AlertBanner>
		<StripeCardDialog
			v-model="showAddCardDialog"
			message="Due to RBI regulations, we need to generate a mandate/consent from Indian customers to process auto debit charge from their card. Please add your card details again. Contact support for further details."
		/>
	</div>
</template>
<script>
import AlertBanner from './AlertBanner.vue';
import StripeCardDialog from './StripeCardDialog.vue';

export default {
	name: 'AlertMandateInfo',
	components: { AlertBanner, StripeCardDialog },
	data() {
		return {
			showAddCardDialog: false,
		};
	},
};
</script>
