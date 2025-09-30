<template>
	<div>
		<AlertBanner
			title="Please add your billing address to complete your Frappe Cloud profile."
			type="warning"
		>
			<Button
				class="ml-auto"
				@click="showBillingDetailsDialog = true"
				variant="outline"
			>
				Update Address
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
