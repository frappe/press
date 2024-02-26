<template>
	<div class="@container" v-if="plans.length">
		<div class="grid grid-cols-2 gap-3 @3xl:grid-cols-4">
			<button
				v-for="(plan, i) in plans"
				:key="plan.name"
				class="flex flex-col overflow-hidden rounded border text-left hover:bg-gray-50"
				:class="[
					modelValue === plan.name
						? 'border-gray-900 ring-1 ring-gray-900'
						: 'border-gray-300',
					{
						'pointer-events-none': plan.disabled
					}
				]"
				@click="$emit('update:modelValue', plan.name)"
			>
				<div
					class="w-full border-b p-3"
					:class="[
						modelValue === plan.name
							? 'border-gray-900 ring-1 ring-gray-900'
							: ''
					]"
				>
					<div class="flex items-center justify-between">
						<div class="text-lg">
							<span class="font-medium text-gray-900">
								{{ $format.planTitle(plan) }}
							</span>
							<span class="text-gray-700"> /mo</span>
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
						/day
					</div>
				</div>
				<div class="p-3 text-p-sm text-gray-800">
					<div>
						<span>{{ plan.vcpu }} </span>
						<span class="ml-1 text-gray-600">
							{{ $format.plural(plan.vcpu, 'vCPU', 'vCPUs') }}
						</span>
					</div>
					<div>
						<span>
							{{ $format.bytes(plan.memory, 0, 2) }}
						</span>
						<span class="text-gray-600"> Memory </span>
					</div>
					<div>
						<span>
							{{ $format.bytes(plan.disk, 0, 2) }}
						</span>
						<span class="text-gray-600"> Disk </span>
					</div>
					<div>
						<span>
							{{ plan.instance_type }}
						</span>
						<span class="text-gray-600"> Instance Type </span>
					</div>
				</div>
			</button>
		</div>
	</div>
	<div v-else class="flex h-24 items-center justify-center">
		<div class="text-gray-600">No plans available</div>
	</div>
</template>

<script>
export default {
	props: ['modelValue', 'plans'],
	emits: ['update:modelValue']
};
</script>
