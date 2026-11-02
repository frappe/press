<template>
	<div
		class="flex flex-col rounded-lg text-base text-ink-gray-9 shadow dark:border"
	>
		<div class="flex items-center justify-between gap-4 px-4 py-3">
			<div class="text-lg font-semibold">Contracts</div>
			<Button
				v-if="canOrder"
				variant="solid"
				label="New contract"
				@click="emit('new')"
			/>
		</div>
		<div
			class="hidden grid-cols-4 border-y bg-surface-gray-1 px-4 py-2 text-sm text-ink-gray-6 sm:grid"
		>
			<span>Contract</span>
			<span>Status</span>
			<span>Yearly price</span>
			<span>Period</span>
		</div>
		<div class="divide-y">
			<component
				:is="hasDetails(row) ? 'router-link' : 'div'"
				v-for="row in contracts"
				:key="row.name"
				:to="hasDetails(row) ? { name: 'Contract', params: { name: row.name } } : undefined"
				class="grid grid-cols-1 items-center gap-2 px-4 py-3 sm:grid-cols-4 sm:gap-0"
				:class="{ 'hover:bg-surface-gray-1': hasDetails(row) }"
			>
				<div>
					<div class="font-medium">{{ row.plan_title }} plan</div>
					<div class="text-sm text-ink-gray-6">{{ row.name }}</div>
				</div>
				<div>
					<Badge :theme="statusTheme(row.status)" :label="row.status" />
				</div>
				<div>{{ money(row.yearly_price, row.currency) }}</div>
				<div class="text-ink-gray-7">{{ period(row) }}</div>
			</component>
		</div>
	</div>
</template>

<script setup>
import { Badge, Button } from 'frappe-ui'
import { formatDate, money, statusTheme } from './format'

defineProps({
	contracts: { type: Array, required: true },
	canOrder: { type: Boolean, default: false },
})
const emit = defineEmits(['new'])

// A cancelled or unpaid order has no agreement or payments to open.
const hasDetails = (row) => ['Pending Signature', 'Active'].includes(row.status)

const period = (row) =>
	hasDetails(row)
		? `Since ${formatDate(row.start_date)}, price locked until ${formatDate(row.price_locked_until)}`
		: '—'
</script>
