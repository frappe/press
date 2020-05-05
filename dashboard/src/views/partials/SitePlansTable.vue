<template>
	<div v-if="plans.length">
		<div
			class="flex px-4 py-3 text-sm text-gray-600 border border-b-0 bg-gray-50 rounded-t-md"
		>
			<div class="w-10"></div>
			<div class="w-1/2">Plan</div>
			<div class="w-1/2">CPU Time</div>
		</div>
		<div
			class="flex px-4 py-3 text-sm text-left border border-b-0 cursor-pointer focus-within:shadow-outline"
			:class="[
				selectedPlan === plan ? 'bg-blue-100' : 'hover:bg-blue-50',
				{
					'border-b rounded-b-md': i === plans.length - 1,
					'pointer-events-none': plan.disabled
				}
			]"
			v-for="(plan, i) in plans"
			:key="plan.name"
			@click="$emit('change', plan)"
		>
			<div class="flex items-center w-10">
				<input
					type="radio"
					class="form-radio"
					:checked="selectedPlan === plan"
					@change="e => (selectedPlan = e.target.checked ? plan : null)"
				/>
			</div>
			<div class="w-1/2" :class="{ 'opacity-25': plan.disabled }">
				<span class="font-semibold">
					{{ plan.plan_title }}
				</span>
				<span> /mo</span>
			</div>
			<div class="w-1/2 text-gray-700" :class="{ 'opacity-25': plan.disabled }">
				{{ plan.cpu_time_per_day }}
				{{ $plural(plan.concurrent_users, 'hour', 'hours') }} / day
			</div>
		</div>
		<div class="mt-2 text-sm text-gray-900" v-if="selectedPlan">
			This plan is ideal for
			{{ selectedPlan.concurrent_users }} concurrent
			{{ $plural(selectedPlan.concurrent_users, 'user', 'users') }}. It will
			allow the CPU execution time equivalent to
			{{ selectedPlan.cpu_time_per_day }}
			{{ $plural(selectedPlan.cpu_time_per_day, 'hour', 'hours') }} per day.
		</div>
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
