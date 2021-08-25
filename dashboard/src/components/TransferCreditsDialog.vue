<template>
	<Dialog
		:show="show"
		@change="$emit('update:show', $event)"
		title="Transfer Credits from ERPNext.com"
	>
		<TransferCredits
			:minimumAmount="minimumAmount"
			@success="$emit('success')"
			@cancel="$emit('update:show', false)"
		/>
	</Dialog>
</template>
<script>
import TransferCredits from './TransferCredits.vue';
export default {
	name: 'TransferCreditsDialog',
	components: {
		TransferCredits
	},
	props: ['show', 'minimumAmount']
};
</script>
