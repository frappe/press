<template>
	<AlertBanner
		title="Your card has expired. Please update your payment details."
		type="warning"
	>
		<Button class="ml-auto" route="/billing" variant="outline">
			Update Card
		</Button>
	</AlertBanner>
</template>
<script>
import AlertBanner from './AlertBanner.vue';

export default {
	name: 'AlertCardExpired',
	components: { AlertBanner },
};
</script>
