<template>
	<div v-if="plans.length">
		<div
			class="bg-gray-0 flex rounded-t-md border border-b-0 px-4 py-3 text-base text-gray-800"
		>
			<div class="w-10"></div>
			<div class="w-1/4">Plan</div>
			<div class="w-1/4">vCPU</div>
			<div class="w-1/4">Memory</div>
			<div class="w-1/4">Instance Type</div>
			<div class="w-1/4">Disk</div>
		</div>
		<div
			class="focus-within:shadow-outline flex cursor-pointer border px-4 py-3 text-left text-base"
			:class="[
				selectedPlan === plan ? 'bg-blue-50' : 'hover:bg-blue-50',
				{
					'rounded-b-md border-b': i === plans.length - 1,
					'border-b-0': i !== plans.length - 1,
					'pointer-events-none': plan.disabled
				}
			]"
			v-for="(plan, i) in plans"
			:key="plan.name"
			@click="$emit('update:selectedPlan', plan)"
		>
			<div class="flex w-10 items-center">
				<input
					type="radio"
					class="form-radio"
					:checked="selectedPlan === plan"
					@change="e => (selectedPlan = e.target.checked ? plan : null)"
				/>
			</div>
			<div class="w-1/4 text-gray-900" :class="{ 'opacity-25': plan.disabled }">
				<span class="font-semibold">
					{{ $planTitle(plan) }}
				</span>
				<span v-if="plan.price_usd > 0"> /mo</span>
			</div>
			<div class="w-1/4 text-gray-900" :class="{ 'opacity-25': plan.disabled }">
				{{ plan.vcpu }}
				{{ $plural(plan.vcpu, 'vCPU', 'vCPUs') }}
			</div>
			<div class="w-1/4 text-gray-900" :class="{ 'opacity-25': plan.disabled }">
				{{ formatBytes(plan.memory, 0, 2) }}
			</div>
			<div class="w-1/4 text-gray-900" :class="{ 'opacity-25': plan.disabled }">
				{{ plan.instance_type }}
			</div>
			<div class="w-1/4 text-gray-900" :class="{ 'opacity-25': plan.disabled }">
				{{ formatBytes(plan.disk, 0, 3) }}
			</div>
		</div>
	</div>
	<div class="text-center" v-else>
		<Button :loading="true">Loading</Button>
	</div>
</template>

<script>
export default {
	name: 'ServerPlansTable',
	props: ['plans', 'selectedPlan'],
	emits: ['update:selectedPlan']
};
</script>
