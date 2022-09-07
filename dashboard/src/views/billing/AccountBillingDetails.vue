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
				$resources.billingDetails.reload();
			"
		/>
		<div class="divide-y" v-if="$resources.billingDetails.data">
			<ListItem
				title="Billing Name"
				:description="$resources.billingDetails.data.billing_name"
			/>
			<ListItem
				title="Billing Address"
				:description="
					$resources.billingDetails.data.billing_address || 'Not set'
				"
			/>
			<ListItem
				v-if="$account.team.country == 'India'"
				title="Tax ID"
				:description="$resources.billingDetails.data.gstin || 'Not set'"
			/>
		</div>
	</Card>
</template>
<script>
import { defineAsyncComponent } from 'vue';

export default {
	name: 'AccountBillingDetails',
	emits: ['updated'],
	components: {
		UpdateBillingDetails: defineAsyncComponent(() =>
			import('@/components/UpdateBillingDetails.vue')
		)
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
