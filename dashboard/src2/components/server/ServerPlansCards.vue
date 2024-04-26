<template>
	<PlansCards :plans="plansOption" v-model="selectedPlan" />
</template>

<script>
import PlansCards from '../PlansCards.vue';

export default {
	props: ['modelValue', 'plans'],
	emits: ['update:modelValue'],
	components: {
		PlansCards
	},
	computed: {
		plansOption() {
			return this.plans.map(plan => {
				return {
					...plan,
					features: [
						{
							label: 'vCPUs',
							value: plan.vcpu
						},
						{
							label: 'Memory',
							value: this.$format.bytes(plan.memory, 0, 2)
						},
						{
							label: 'Disk',
							value: `${plan.disk} GB`
						},
						{
							label: 'Instance Type',
							value: plan.instance_type
						}
					]
				};
			});
		},
		selectedPlan: {
			get() {
				return this.modelValue;
			},
			set(value) {
				this.$emit('update:modelValue', value);
			}
		}
	}
};
</script>
