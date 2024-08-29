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
						'pointer-events-none opacity-50': plan.disabled
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
								<template v-if="plan.label">
									{{ plan.label }}
								</template>
								<template v-else>
									{{ $format.planTitle(plan) }}
									<span v-if="plan.price_inr" class="text-gray-700"> / mo</span>
								</template>
							</span>
						</div>
					</div>
					<div class="mt-1 text-sm text-gray-600">
						<template v-if="plan.sublabel">
							{{ plan.sublabel }}
						</template>
						<template v-else>
							{{
								$format.userCurrency(
									$format.pricePerDay(
										$team.doc.currency === 'INR'
											? plan.price_inr
											: plan.price_usd
									)
								)
							}}
							/ day
						</template>
					</div>
				</div>
				<div class="p-3 text-p-sm text-gray-800">
					<div v-for="feature in plan.features">
						<div v-if="feature.value" class="flex space-x-2">
							<component
								v-if="feature.icon"
								:is="_icon(feature.icon, 'mt-1 h-3 w-4 shrink-0 text-gray-900')"
							/>
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
import { icon } from '../utils/components';

export default {
	props: ['plans', 'modelValue'],
	methods: {
		_icon(iconName, classes) {
			return icon(iconName, classes);
		}
	}
};
</script>
