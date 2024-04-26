<template>
	<AlertBanner :title="title" type="error">
		<Button class="ml-auto" variant="outline" @click="show"> View </Button>
	</AlertBanner>
</template>
<script>
import AlertBanner from './AlertBanner.vue';
import { addressableErrorDialog } from '../utils/components';

export default {
	name: 'AlertAddressableError',
	components: { AlertBanner },
	emits: ['done'],
	props: {
		name: String,
		title: String
	},
	methods: {
		show() {
			addressableErrorDialog(this.name, () => this.$emit('done'));
		}
	}
};
</script>
