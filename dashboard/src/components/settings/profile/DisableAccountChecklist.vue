<template>
	<div class="mt-4 rounded border p-3 text-base">
		<p class="mb-2 font-medium text-ink-gray-9">
			Before you disable the account:
		</p>
		<div v-for="step in steps" :key="step.label" class="flex gap-2 py-1">
			<lucide-circle-check
				v-if="step.done"
				class="mt-0.5 h-4 w-4 shrink-0 text-ink-green-3"
			/>
			<lucide-circle-alert
				v-else
				class="mt-0.5 h-4 w-4 shrink-0 text-ink-amber-3"
			/>
			<div class="text-ink-gray-7">
				{{ step.label }}
				<router-link
					v-if="!step.done"
					:to="step.route"
					class="ml-1 underline"
					@click="$emit('navigate')"
				>
					{{ step.linkLabel }}
				</router-link>
			</div>
		</div>
		<a
			:href="docsLink"
			target="_blank"
			class="mt-2 inline-block text-sm text-ink-gray-6 underline"
		>
			Read how to disable the account
		</a>
	</div>
</template>

<script setup>
import { createResource } from 'frappe-ui'
import { computed } from 'vue'
import { getTeam } from '../../../data/team'
import { userCurrency } from '../../../utils/format'

const props = defineProps({
	unpaidInvoices: { type: Array, default: () => [] },
	draftInvoice: { type: Object, default: null },
})
defineEmits(['navigate'])

const docsLink = 'https://docs.frappe.io/cloud/billing/disable-account'
const team = getTeam()

const activeServers = createResource({
	url: 'press.api.account.active_servers',
	auto: true,
})

// Same rule as has_unsettled_invoices in team.py
const minimumAmount = computed(() =>
	team.doc?.currency === 'INR' ? 450 : 5,
)

const amountDue = computed(() => {
	const unpaid = (props.unpaidInvoices || []).reduce(
		(total, invoice) => total + (invoice.amount_due || 0),
		0,
	)
	return unpaid + (props.draftInvoice?.amount_due || 0)
})

const steps = computed(() => {
	const invoicesClear = amountDue.value <= minimumAmount.value
	const serverCount = activeServers.data?.length || 0
	return [
		{
			done: invoicesClear,
			label: invoicesClear
				? 'No invoices to pay.'
				: `Pay the open invoices (${userCurrency(amountDue.value)}).`,
			route: { name: 'BillingInvoices' },
			linkLabel: 'Go to invoices',
		},
		{
			done: serverCount === 0,
			label: serverCount
				? `Drop the active servers (${serverCount}).`
				: 'No active servers.',
			route: { name: 'Server List' },
			linkLabel: 'Go to servers',
		},
	]
})
</script>
