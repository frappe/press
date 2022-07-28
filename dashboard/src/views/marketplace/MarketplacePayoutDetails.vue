<script setup>
import useResource from '@/composables/resource';

const props = defineProps({
	payoutOrderName: {
		type: String,
		required: true
	}
});

const payout = useResource({
	method: 'press.api.marketplace.get_payout_details',
	auto: true,
	params: {
		name: props.payoutOrderName
	},
    onSuccess(d) {
        console.log(d);
    }
});
</script>
<template>
	<div>
		<Button v-if="payout.loading" :loading="true">Loading</Button>

		<div v-if="payout.data">
			
		</div>

		<ErrorMessage :error="payout.error" />
	</div>
</template>
