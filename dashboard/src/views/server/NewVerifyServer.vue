<template>
	<div>
		<div class="mb-2">
			<p class="text-base text-gray-700">
				You have selected following server plans
			</p>
		</div>
		<div clas="mt-4">
			<label class="text-base font-semibold">Application Server</label>
			<div
				class="focus-within:shadow-outline mt-2 flex rounded-md border px-4 py-3 text-left text-base"
			>
				<div class="w-1/4 text-gray-900">
					<span class="font-semibold">
						{{ $planTitle(selectedAppPlan) }}
					</span>
					<span v-if="selectedAppPlan.price_usd > 0"> /mo</span>
				</div>
				<div class="w-1/4 text-gray-900">
					{{ selectedAppPlan.vcpu }}
					{{ $plural(selectedAppPlan.vcpu, 'vCPU', 'vCPUs') }}
				</div>
				<div class="w-1/4 text-gray-900">
					{{ formatBytes(selectedAppPlan.memory, 0, 2) }}
				</div>
				<div class="w-1/4 text-gray-900">
					{{ selectedAppPlan.instance_type }}
				</div>
				<div class="w-1/4 text-gray-900">
					{{ formatBytes(selectedAppPlan.disk, 0, 3) }}
				</div>
			</div>
		</div>
		<div class="mt-4">
			<label class="text-base font-semibold">Database Server</label>
			<div
				class="focus-within:shadow-outline mt-2 flex rounded-md border px-4 py-3 text-left text-base"
			>
				<div class="w-1/4 text-gray-900">
					<span class="font-semibold">
						{{ $planTitle(selectedDBPlan) }}
					</span>
					<span v-if="selectedDBPlan.price_usd > 0"> /mo</span>
				</div>
				<div class="w-1/4 text-gray-900">
					{{ selectedDBPlan.vcpu }}
					{{ $plural(selectedDBPlan.vcpu, 'vCPU', 'vCPUs') }}
				</div>
				<div class="w-1/4 text-gray-900">
					{{ formatBytes(selectedDBPlan.memory, 0, 2) }}
				</div>
				<div class="w-1/4 text-gray-900">
					{{ selectedDBPlan.instance_type }}
				</div>
				<div class="w-1/4 text-gray-900">
					{{ formatBytes(selectedDBPlan.disk, 0, 3) }}
				</div>
			</div>
		</div>
		<div class="mt-4">
			<p class="text-base text-gray-700">
				Your monthly bill will be
				<span class="font-semibold">{{ $planTitle(totalPlan) }}</span>
			</p>
		</div>
	</div>
</template>
<script>
export default {
	name: 'VerifyServer',
	props: ['options', 'selectedAppPlan', 'selectedDBPlan'],
	components: {},
	computed: {
		totalPlan() {
			return {
				plan_title:
					this.selectedAppPlan.plan_title + this.selectedDBPlan.plan_title,
				price_inr:
					this.selectedAppPlan.price_inr + this.selectedDBPlan.price_inr,
				price_usd:
					this.selectedAppPlan.price_usd + this.selectedDBPlan.price_usd
			};
		}
	}
};
</script>
