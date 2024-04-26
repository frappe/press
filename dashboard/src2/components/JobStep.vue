<template>
	<FoldStep
		:open="Boolean(step.isOpen)"
		:caption="step.duration"
		:title="step.title"
		:body="step.output || 'No Output'"
		:status="step.status"
		@toggle="step.isOpen = !step.isOpen"
	/>
</template>
<script>
import FoldStep from './FoldStep.vue';

export default {
	name: 'JobStep',
	props: {
		step: {
			type: Object,
			required: true
		}
	},
	components: { FoldStep }
};
</script>
