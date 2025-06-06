<template>
	<div class="flex flex-1 flex-col gap-8 overflow-y-auto px-60 py-6">
		deal details
		<LeadFollowup />
	</div>
</template>
<script>
import LeadFollowup from './LeadFollowup.vue';
export default {
	name: 'LeadDealDetails',
	components: {
		LeadFollowup,
	},
};
</script>
