<template>
	<div class="flex flex-col gap-6">
		<div
			class="flex flex-col rounded-lg text-base text-ink-gray-9 shadow dark:border"
		>
			<div class="flex items-start justify-between gap-4 px-4 py-3">
				<div class="flex flex-col gap-1.5">
					<div class="text-lg font-semibold">
						{{ contract.plan_title }}
						plan
					</div>
					<div class="text-ink-gray-7">
						{{ contract.billing_name }}
						· {{ contract.name }}
					</div>
				</div>
				<Badge size="lg" :theme="statusTheme" :label="contract.status" />
			</div>

			<ContractProgress class="px-4 pb-4 pt-1" :status="contract.status" />

			<div
				class="grid grid-cols-1 divide-y border-t sm:grid-cols-3 sm:divide-x sm:divide-y-0"
			>
				<div
					v-for="fact in facts"
					:key="fact.label"
					class="flex flex-col gap-1 px-4 py-3"
				>
					<div class="text-sm text-ink-gray-6">{{ fact.label }}</div>
					<div class="font-medium text-ink-gray-9">{{ fact.value }}</div>
					<div v-if="fact.hint" class="text-sm text-ink-gray-6">
						{{ fact.hint }}
					</div>
				</div>
			</div>

			<div
				class="m-1.5 flex items-center justify-between gap-4 rounded-lg bg-surface-gray-1 px-2.5 py-2"
			>
				<div class="flex items-center gap-2 text-ink-gray-8">
					<LucideFileSignature class="h-4 w-4 shrink-0" />
					<span v-if="contract.signed_contract">
						Agreement signed on {{ formatDate(contract.agreement_date) }}
					</span>
					<span v-else>
						Frappe is signing your agreement. We will email you the signed copy.
					</span>
				</div>
				<Button
					v-if="contract.signed_contract"
					label="Download contract"
					:link="contract.signed_contract"
				>
					<template #prefix><LucideDownload class="h-4 w-4" /></template>
				</Button>
			</div>
		</div>

		<div
			class="flex flex-col rounded-lg text-base text-ink-gray-9 shadow dark:border"
		>
			<div class="px-4 py-3 text-lg font-semibold">Coverage</div>
			<div class="flex flex-col gap-3 px-4 pb-4">
				<div class="flex items-center gap-2 text-ink-gray-7">
					<LucideLayoutGrid class="h-4 w-4" />
					<span>All core apps built by Frappe</span>
				</div>
				<div
					v-if="contract.legal_entities_covered"
					class="flex items-center gap-2 text-ink-gray-7"
				>
					<LucideBuilding2 class="h-4 w-4" />
					<span>{{ contract.legal_entities_covered }}</span>
				</div>
			</div>
		</div>

		<ContractPayments :contract="contract" />
	</div>
</template>

<script setup>
import { Badge, Button } from 'frappe-ui'
import { computed } from 'vue'
import ContractPayments from './ContractPayments.vue'
import ContractProgress from './ContractProgress.vue'
import { formatDate, money } from './format'

const props = defineProps({ contract: { type: Object, required: true } })

const statusTheme = computed(
	() =>
		({ Active: 'green', 'Pending Signature': 'orange' })[
			props.contract.status
		] || 'gray',
)

const facts = computed(() => {
	const contract = props.contract
	return [
		{
			label: 'Yearly price',
			value: money(contract.yearly_price, contract.currency),
			hint: 'Excluding taxes',
		},
		{
			label: 'Price locked until',
			value: formatDate(contract.price_locked_until),
			hint: `${contract.price_lock_years} year price lock`,
		},
		{
			label: 'Next renewal',
			value: formatDate(contract.next_renewal.date),
			hint: money(contract.next_renewal.amount, contract.currency),
		},
	]
})
</script>
