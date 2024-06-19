<template>
	<AlertBanner
		title="Due to RBI regulations, we need to collect a mandate/consent from you to process payments from your card. Please remove and add your card again. Contact support for any further details."
		type="warning"
	>
		<Button class="ml-auto shrink-0" route="/billing" variant="outline">
			Update Card
		</Button>
	</AlertBanner>
</template>
<script>
import AlertBanner from './AlertBanner.vue';

export default {
	name: 'AlertMandateInfo',
	components: { AlertBanner }
};
</script>
