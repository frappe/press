<template>
	<Card
		title="Billing details"
		subtitle="Your billing details are shown in the monthly invoice"
	>
		<template #actions>
			<Button @click="editBillingDetails = true">Change</Button>
		</template>
		<UpdateBillingDetails
			v-model="editBillingDetails"
			@updated="
				editBillingDetails = false;
				billingDetails.reload();
			"
		/>
		<div class="divide-y" v-if="billingDetails.data">
			<ListItem
				title="Billing Name"
				:description="billingDetails.data.billing_name"
			/>
			<ListItem
				title="Billing Address"
				:description="billingDetails.data.billing_address || 'Not set'"
			/>
			<ListItem title="Tax ID" :description="billingDetails.data.gstin || 'Not set'" />
		</div>
	</Card>
</template>
<script>
export default {
	name: 'AccountBillingDetails',
	components: {
		UpdateBillingDetails: () => import('@/components/UpdateBillingDetails')
	},
	resources: {
		billingDetails: 'press.api.billing.details'
	},
	data() {
		return {
			editBillingDetails: false
		};
	}
};
</script>
