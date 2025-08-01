<template>
	<Dialog
		:options="{
			title: `Select Plan for ${app?.app_title || app?.title}`,
			size: '3xl',
			actions: [
				{
					label: 'Select Plan',
					variant: 'solid',
					disabled: !selectedPlan,
					onClick: () => {
						$emit('plan-select', selectedPlan);
						show = false;
					},
				},
			],
		}"
		v-model="show"
	>
		<template #body-content>
			<PlansCards v-model="selectedPlan" :plans="plans" />
		</template>
	</Dialog>
</template>

<script>
import PlansCards from '../PlansCards.vue';

export default {
	props: ['app', 'modelValue', 'currentPlan'],
	emits: ['plan-select', 'update:modelValue'],
	components: {
		PlansCards,
	},
	data() {
		return {
			selectedPlan: this.currentPlan,
		};
	},
	computed: {
		show: {
			get() {
				return this.modelValue;
			},
			set(val) {
				this.$emit('update:modelValue', val);
				if (!val) this.selectedPlan = null;
			},
		},
		plans() {
			return this.app.plans.map((plan) => {
				return {
					label:
						plan.price_inr === 0 || plan.price_usd === 0
							? 'Free'
							: `${this.$format.userCurrency(
									this.$team.doc.currency === 'INR'
										? plan.price_inr
										: plan.price_usd,
								)}/mo`,
					sublabel: ' ',
					...plan,
					features: plan.features.map((f) => ({
						value: f,
						icon: 'check-circle',
					})),
				};
			});
		},
	},
};
</script>
