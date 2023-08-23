<template>
	<Alert title="Account Setup" v-if="!$account.hasBillingInfo">
		You haven't added your billing information yet. Add it to start creating
		sites.
		<template #actions>
			<Button
				variant="solid"
				@click="showDialog = true"
				class="whitespace-nowrap"
			>
				Add Billing Information
			</Button>
		</template>
		<BillingInformationDialog v-model="showDialog" v-if="showDialog" />
	</Alert>
</template>
<script>
import { defineAsyncComponent } from 'vue';

export default {
	name: 'AlertBillingInformation',
	components: {
		BillingInformationDialog: defineAsyncComponent(() =>
			import('./BillingInformationDialog.vue')
		)
	},
	data() {
		return {
			showDialog: false
		};
	}
};
</script>
