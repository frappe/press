<template>
	<AlertBanner
		title="Add a payment mode to start creating sites, bench groups, and more."
		type="warning"
	>
		<Button class="ml-auto" @click="addPaymentMode" variant="outline">
			Add payment mode
		</Button>
	</AlertBanner>
</template>
<script>
import AlertBanner from './AlertBanner.vue';

export default {
	name: 'AlertAddPaymentMode',
	components: { AlertBanner },
	methods: {
		addPaymentMode() {
			this.$team.reload();
			this.$router.push('/welcome');
		}
	}
};
</script>
