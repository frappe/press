<template>
	<div class="@container" v-if="plans.length">
		<div class="grid grid-cols-2 gap-3 @xl:grid-cols-3">
			<Tooltip
				v-for="(plan, i) in plans"
				:key="plan.name"
				:text="
					plan?.machine_unavailable ? 'Machine is currently unavailable' : ''
				"
				:disabled="!plan?.machine_unavailable"
				:hoverDelay="0.1"
				placement="top"
			>
				<button
					class="flex flex-col overflow-hidden rounded-md border text-left hover:bg-gray-50"
					:class="[
						modelValue?.name === plan?.name
							? 'border-gray-900 ring-1 ring-gray-900'
							: 'border-gray-300',
						{
							'pointer-events-none opacity-50': plan?.disabled,
							'opacity-50': plan?.machine_unavailable,
						},
					]"
					@click="
						plan?.machine_unavailable ? null : $emit('update:modelValue', plan)
					"
				>
					<div
						class="h-16 w-full border-b p-3"
						:class="[
							modelValue === plan ? 'border-gray-900 ring-1 ring-gray-900' : '',
						]"
					>
						<div class="flex items-center justify-between">
							<div class="flex w-full items-center text-lg">
								<span class="truncate font-medium text-gray-900">
									<!-- Needed for app plan selector -->
									<template v-if="plan.label">{{ plan.label }}</template>
									<template v-if="hourlyPricing">
										{{ $format.planTitleHourly(plan) }}
										<span v-if="plan.price_inr" class="text-gray-700"
											>/hour</span
										>
									</template>
									<template v-else>
										{{ $format.planTitle(plan) }}
										<span v-if="plan.price_inr" class="text-gray-700">/mo</span>
									</template>
								</span>
								<Tooltip text="Product support included">
									<lucide-badge-check
										class="ml-1 h-4 w-6 text-gray-600"
										v-if="plan.support_included"
									/>
								</Tooltip>
							</div>
						</div>
						<div class="mt-1 text-sm text-gray-600" v-if="!hourlyPricing">
							<template v-if="plan.sublabel">
								{{ plan.sublabel }}
							</template>
							<template v-else-if="plan.price_inr || plan.price_usd">
								{{
									$format.userCurrency(
										$format.pricePerDay(
											$team.doc.currency === 'INR'
												? plan.price_inr
												: plan.price_usd,
										),
									)
								}}/day
							</template>
						</div>
					</div>
					<div class="p-3 text-p-sm text-gray-800">
						<div v-for="feature in plan.features">
							<div v-if="feature.value" class="flex space-x-2">
								<component
									v-if="feature.icon"
									:is="
										_icon(feature.icon, 'mt-1 h-3 w-4 shrink-0 text-gray-900')
									"
								/>
								<span>{{ feature.value }} </span>
								<span class="ml-1 text-gray-600">
									{{ feature.label }}
								</span>
							</div>
						</div>
					</div>
				</button>
			</Tooltip>
		</div>
	</div>
	<div v-else class="flex h-6 items-center">
		<div class="text-base text-gray-600">No plans available</div>
	</div>
</template>

<script>
import { Tooltip } from 'frappe-ui';
import { icon } from '../utils/components';

export default {
	components: {
		Tooltip,
	},
	props: {
		modelValue: {
			type: [String, Object, Number, Boolean],
			default: null,
		},
		plans: {
			type: Array,
			default: () => [],
		},
		hourlyPricing: {
			type: Boolean,
			default: false,
		},
	},
	methods: {
		_icon(iconName, classes) {
			return icon(iconName, classes);
		},
	},
};
</script>
