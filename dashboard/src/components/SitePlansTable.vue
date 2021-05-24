<template>
	<div v-if="plans.length">
		<div
			class="flex px-4 py-3 text-base text-gray-800 border border-b-0 bg-gray-0 rounded-t-md"
		>
			<div class="w-10"></div>
			<div class="w-1/4">Plan</div>
			<div class="w-1/4">CPU Time</div>
			<div class="w-1/4">Database</div>
			<div class="w-1/4">Disk</div>
		</div>
		<div
			class="flex px-4 py-3 text-base text-left border border-b-0 cursor-pointer focus-within:shadow-outline"
			:class="[
				selectedPlan === plan ? 'bg-blue-50' : 'hover:bg-blue-50',
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
			<div class="w-1/4 text-gray-900" :class="{ 'opacity-25': plan.disabled }">
				<span class="font-semibold">
					{{ plan.plan_title }}
				</span>
				<span> /mo</span>
			</div>
			<div class="w-1/4 text-gray-900" :class="{ 'opacity-25': plan.disabled }">
				{{ plan.cpu_time_per_day }}
				{{ $plural(plan.concurrent_users, 'hour', 'hours') }} / day
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
