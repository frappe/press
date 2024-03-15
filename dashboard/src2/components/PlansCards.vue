<template>
	<div class="@container" v-if="plans.length">
		<div class="grid grid-cols-2 gap-3 @xl:grid-cols-3">
			<button
				v-for="(plan, i) in plans"
				:key="plan.name"
				class="flex flex-col overflow-hidden rounded border text-left hover:bg-gray-50"
				:class="[
					modelValue?.name === plan?.name
						? 'border-gray-900 ring-1 ring-gray-900'
						: 'border-gray-300',
					{
						'pointer-events-none': plan.disabled
					}
				]"
				@click="$emit('update:modelValue', plan)"
			>
				<div
					class="w-full border-b p-3"
					:class="[
						modelValue === plan ? 'border-gray-900 ring-1 ring-gray-900' : ''
					]"
				>
					<div class="flex items-center justify-between">
						<div class="text-lg">
							<span class="font-medium text-gray-900">
								{{ $format.planTitle(plan) }}
							</span>
							<span v-if="plan.price_inr" class="text-gray-700"> / mo</span>
						</div>
					</div>
					<div class="mt-1 text-sm text-gray-600">
						{{
							$format.userCurrency(
								$format.pricePerDay(
									$team.doc.currency === 'INR' ? plan.price_inr : plan.price_usd
								)
							)
						}}
						/ day
					</div>
				</div>
				<div class="p-3 text-p-sm text-gray-800">
					<div v-for="feature in plan.features">
						<div v-if="feature.value">
							<span>{{ feature.value }} </span>
							<span class="ml-1 text-gray-600">
								{{ feature.label }}
							</span>
						</div>
					</div>
				</div>
			</button>
		</div>
	</div>
	<div v-else class="flex h-6 items-center">
		<div class="text-base text-gray-600">No plans available</div>
	</div>
</template>

<script>
export default {
	props: ['plans', 'modelValue']
};
</script>
