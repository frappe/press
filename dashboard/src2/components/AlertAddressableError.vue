<template>
	<AlertBanner :title="title" type="error">
		<Button class="ml-auto" variant="outline" @click="show"> View </Button>
	</AlertBanner>
</template>
<script>
import AlertBanner from './AlertBanner.vue';
import { addressableErrorDialog } from '../utils/components';

export default {
	name: 'AlertAddPaymentMode',
	components: { AlertBanner },
	props: {
		name: String,
		title: String
	},
	methods: {
		show() {
			addressableErrorDialog(this.name);
		}
	}
};
</script>
