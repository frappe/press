<template>
	<Dialog
		:options="{
			title: `Select Plan for ${app?.app_title}`,
			size: '3xl',
			actions: [
				{
					label: 'Select Plan',
					variant: 'solid',
					disabled: !selectedPlan,
					onClick: () => {
						$emit('plan-select', selectedPlan);
						show = false;
					}
				}
			]
		}"
		v-model="show"
	>
		<template #body-content>
			<div class="grid grid-cols-3 gap-3">
				<button
					v-for="plan in app.plans"
					:key="plan.name"
					class="flex flex-col overflow-hidden rounded border text-left hover:bg-gray-50"
					:class="[
						selectedPlan?.name === plan.name
							? 'border-gray-900 ring-1 ring-gray-900'
							: 'border-gray-300'
					]"
					@click="selectedPlan = plan"
				>
					<div
						class="w-full border-b p-3"
						:class="[
							selectedPlan?.name === plan.name
								? 'border-gray-900 ring-1 ring-gray-900'
								: ''
						]"
					>
						<div class="flex items-center justify-between">
							<div class="text-lg">
								<span class="font-medium text-gray-900">
									{{ plan.plan }}
								</span>
							</div>
						</div>
					</div>
					<div class="p-3 text-p-sm text-gray-800">
						<div v-for="feature in plan.features">
							<span>{{ feature }}</span>
						</div>
					</div>
				</button>
			</div>
		</template>
	</Dialog>
</template>

<script>
export default {
	props: ['app', 'modelValue', 'currentPlan'],
	emits: ['plan-select', 'update:modelValue'],
	data() {
		return {
			selectedPlan: this.currentPlan
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
			}
		}
	}
};
</script>
