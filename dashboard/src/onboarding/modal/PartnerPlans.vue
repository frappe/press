<script setup>
// import { formatCurrency } from '@/utils/format';
import { createResource, ErrorMessage, LoadingText } from 'frappe-ui'
import { computed } from 'vue'

const partnerTiersResource = createResource({
	url: 'press.api.client.get_list',
	params: {
		doctype: 'Partner Tier',
		filters: { enabled: 1 },
		fields: ['name', 'target_in_usd', 'target_in_inr'],
		order_by: 'target_in_usd asc',
	},
	auto: true,
})

const partnerPlans = computed(() => {
	// modify the partnerTiers data with added discount for each tier respectively
	let plans = partnerTiersResource.data?.map((tier) => {
		let discount = 10
		if (tier.name === 'Gold') {
			discount = 25
		} else if (tier.name === 'Silver') {
			discount = 20
		} else if (tier.name === 'Bronze') {
			discount = 15
		} else {
			discount = 10
		}

		return {
			type: tier.name,
			mrr: tier.target_in_usd,
			discount: discount,
		}
	})

	// sort plans by mrr - as map messes up the order
	plans.sort((a, b) => a.mrr - b.mrr)
	return plans
})

const formatCurrency = (amount) => {
	return new Intl.NumberFormat('en-US', {
		style: 'currency',
		currency: 'USD',
	}).format(amount)
}
</script>

<template>
	<div>
		<p class="text-p-base text-ink-gray-6 mb-4">Our partnership tiers:</p>
		<!-- column name -->
		<div
			class="flex items-center justify-between px-3 py-2 bg-surface-gray-1 rounded-md"
		>
			<div class="flex items-center gap-1.5 w-1/3">
				<span class="text-p-base font-medium text-ink-gray-5"> Tier </span>
			</div>
			<div class="flex items-center justify-end gap-1.5 w-1/3">
				<span class="text-p-base font-medium text-ink-gray-5 text-right">
					Min sales/month
				</span>
			</div>
			<div class="flex items-center justify-end gap-1.5 w-1/3">
				<span class="text-p-base font-medium text-ink-gray-5 text-right">
					Hosting discount
				</span>
			</div>
		</div>

		<div class="divide-y">
			<!-- loading state -->
			<div
				v-if="partnerTiersResource.loading"
				class="flex items-center justify-center px-4 py-3"
			>
				<LoadingText />
			</div>

			<!-- error state -->
			<div
				v-else-if="partnerTiersResource.error"
				class="flex items-center justify-center px-4 py-3"
			>
				<ErrorMessage :message="partnerTiersResource.error" />
			</div>

			<!-- data state -->
			<div
				v-else-if="partnerPlans.length > 0"
				v-for="plan in partnerPlans"
				:key="plan.type"
				class="flex items-center justify-between px-3 py-2"
			>
				<div class="flex items-center gap-1.5 w-1/3">
					<span class="text-p-base font-medium text-ink-gray-9">
						{{ plan.type }}
					</span>
					<span v-if="plan.badge">{{ plan.badge }}</span>
				</div>

				<div class="flex items-baseline justify-end gap-1 text-right w-1/3">
					<span class="text-p-base text-ink-gray-6">
						{{ formatCurrency(plan.mrr) }}
					</span>
				</div>

				<div class="text-right w-1/3">
					<span class="text-p-base text-ink-gray-6">
						{{ plan.discount }}%
					</span>
				</div>
			</div>
			<!-- no data state -->
			<div v-else class="flex items-center justify-center px-4 py-3">
				<p class="text-p-base text-ink-gray-6">No partner tiers found</p>
			</div>
		</div>
	</div>
</template>
