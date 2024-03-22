<template>
	<AlertBanner
		title="Add a payment mode to start creating sites, benches, and more."
		type="warning"
	>
		<Button
			class="ml-auto"
			:route="$team.doc.onboarding.complete ? '/billing' : '/welcome'"
			variant="outline"
		>
			Add payment mode
		</Button>
	</AlertBanner>
</template>
<script>
import AlertBanner from './AlertBanner.vue';

export default {
	name: 'AlertAddPaymentMode',
	components: { AlertBanner }
};
</script>
