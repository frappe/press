<template>
	<div v-if="plans.length">
		<div class="my-3 w-full space-y-2">
			<div class="grid grid-cols-2 gap-3">
				<button
					v-for="c in [
						{
							name: 'Standard',
							description: 'Includes standard support and SLAs'
						},
						{
							name: 'Premium',
							description: 'Includes enterprise support and SLAs'
						}
					]"
					:key="c.name"
					@click="planType = c.name"
					:class="[
						planType === c.name
							? 'border-gray-900 ring-1 ring-gray-900 hover:bg-gray-100'
							: 'border-gray-400 bg-white text-gray-900 ring-gray-200 hover:bg-gray-50',
						'flex w-full items-center rounded border p-3 text-left text-base text-gray-900'
					]"
				>
					<div class="flex w-full items-center justify-between space-x-2">
						<span class="text-sm font-medium">
							{{ c.name }}
						</span>
						<Tooltip :text="c.description">
							<i-lucide-info class="h-4 w-4 text-gray-500" />
						</Tooltip>
					</div>
				</button>
			</div>
		</div>
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
			v-for="(plan, i) in planList"
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
				{{ plan.vcpu > 0 ? $plural(plan.vcpu, 'vCPU', 'vCPUs') : '' }}
			</div>
			<div class="w-1/4 text-gray-900" :class="{ 'opacity-25': plan.disabled }">
				{{ plan.memory > 0 ? formatBytes(plan.memory, 0, 2) : 'Any' }}
			</div>
			<div class="w-1/4 text-gray-900" :class="{ 'opacity-25': plan.disabled }">
				{{ plan.instance_type }}
			</div>
			<div class="w-1/4 text-gray-900" :class="{ 'opacity-25': plan.disabled }">
				{{ plan.disk > 0 ? formatBytes(plan.disk, 0, 3) : 'Any' }}
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
	emits: ['update:selectedPlan'],
	data() {
		return {
			planType: 'Standard'
		};
	},
	computed: {
		planList() {
			return this.plans.filter(p => {
				if (this.planType === 'Standard') {
					return p.premium == 0;
				} else {
					return p.premium == 1;
				}
				return False;
			});
		}
	}
};
</script>
