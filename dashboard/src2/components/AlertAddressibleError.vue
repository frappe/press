<template>
	<AlertBanner :title="title" type="error">
		<Button class="ml-auto" variant="outline"> View </Button>
	</AlertBanner>
</template>
<script>
import AlertBanner from './AlertBanner.vue';

export default {
	name: 'AlertAddPaymentMode',
	components: { AlertBanner },
	props: {
		name: String,
		title: String,
		type: {
			type: String,
			default: 'info'
		}
	}
};
</script>
