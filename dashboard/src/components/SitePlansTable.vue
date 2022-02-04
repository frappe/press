<template>
	<div v-if="plans.length">
		<div
			class="bg-gray-0 flex rounded-t-md border border-b-0 px-4 py-3 text-base text-gray-800"
		>
			<div class="w-10"></div>
			<div class="w-1/4">Plan</div>
			<div class="w-1/4">CPU Time</div>
			<div class="w-1/4">Database</div>
			<div class="w-1/4">Disk</div>
		</div>
		<div
			class="focus-within:shadow-outline flex cursor-pointer border border-b-0 px-4 py-3 text-left text-base"
			:class="[
				selectedPlan === plan ? 'bg-blue-50' : 'hover:bg-blue-50',
				{
					'rounded-b-md border-b': i === plans.length - 1,
					'pointer-events-none': plan.disabled
				}
			]"
			v-for="(plan, i) in plans"
			:key="plan.name"
			@click="$emit('change', plan)"
		>
			<div class="flex w-10 items-center">
				<input
					type="radio"
					class="form-radio"
					:checked="selectedPlan === plan"
					@change="(e) => (selectedPlan = e.target.checked ? plan : null)"
				/>
			</div>
			<div class="w-1/4 text-gray-900" :class="{ 'opacity-25': plan.disabled }">
				<span class="font-semibold">
					{{ $planTitle(plan) }}
				</span>
				<span v-if="plan.price_usd > 0"> /mo</span>
			</div>
			<div class="w-1/4 text-gray-900" :class="{ 'opacity-25': plan.disabled }">
				{{ plan.cpu_time_per_day }}
				{{ $plural(plan.cpu_time_per_day, 'hour', 'hours') }} / day
			</div>
			<div class="w-1/4 text-gray-900" :class="{ 'opacity-25': plan.disabled }">
				{{ formatBytes(plan.max_database_usage, 0, 2) }}
			</div>
			<div class="w-1/4 text-gray-900" :class="{ 'opacity-25': plan.disabled }">
				{{ formatBytes(plan.max_storage_usage, 0, 2) }}
			</div>
		</div>
	</div>
	<div class="text-center" v-else>
		<Button :loading="true">Loading</Button>
	</div>
</template>

<script>
export default {
	name: 'SitePlansTable',
	props: ['plans', 'selectedPlan'],
	model: {
		prop: 'selectedPlan',
		event: 'change'
	}
};
</script>
