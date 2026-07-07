<template>
	<FoldStep
		:open="Boolean(step.isOpen)"
		:caption="step.duration"
		:title="step.title"
		:body="step.output || 'No Output'"
		:status="step.status"
		@toggle="handleToggle"
	/>
</template>
<script>
import FoldStep from './FoldStep.vue';

export default {
	name: 'JobStep',
	props: {
		step: {
			type: Object,
			required: true,
		},
		emitToggleEvent: {
			type: Boolean,
			default: false,
		},
	},
	components: { FoldStep },
	methods: {
		handleToggle() {
			if (this.emitToggleEvent) {
				this.$emit('toggleStep', this.step, !this.step.isOpen);
			} else {
				this.step.isOpen = !this.step.isOpen;
			}
		},
	},
};
</script>
