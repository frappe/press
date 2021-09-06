<template>
	<Dialog
		:show="show"
		@change="$emit('update:show', $event)"
		title="Buy Credits"
	>
		<BuyPrepaidCredits
			:minimumAmount="minimumAmount"
			@success="$emit('success')"
			@cancel="$emit('update:show', false)"
		/>
	</Dialog>
</template>
<script>
import BuyPrepaidCredits from './BuyPrepaidCredits.vue';

export default {
	name: 'PrepaidCreditsDialog',
	components: {
		BuyPrepaidCredits
	},
	props: {
		show: {
			default: true
		},
		minimumAmount: {
			default: 0
		}
	}
};
</script>
