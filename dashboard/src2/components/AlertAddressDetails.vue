<template>
	<AlertBanner
		title="Please add your billing address details to complete your Frappe Cloud profile."
		type="warning"
	>
		<Button class="ml-auto" route="/billing" variant="outline">
			Update Address
		</Button>
	</AlertBanner>
</template>
<script>
import AlertBanner from './AlertBanner.vue';

export default {
	name: 'AlertAddressDetails',
	components: { AlertBanner }
};
</script>
