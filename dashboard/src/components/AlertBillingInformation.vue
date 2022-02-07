<template>
	<Alert title="Account Setup" v-if="!$account.hasBillingInfo">
		You haven't added your billing information yet. Add it to start creating
		sites.
		<template #actions>
			<Button type="primary" route="/welcome" class="whitespace-nowrap"
				>Add Billing Information</Button
			>
		</template>
	</Alert>
</template>
<script>
export default {
	name: 'AlertBillingInformation'
};
</script>
