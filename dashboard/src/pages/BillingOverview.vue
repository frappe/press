<template>
	<div
		v-if="team.doc"
		class="flex flex-1 flex-col gap-8 overflow-y-auto px-5 pt-6 md:px-10 lg:px-60"
	>
		<BillingSummary />
		<PaymentDetails />
	</div>
	<div v-else class="mt-12 flex flex-1 items-center justify-center">
		<Spinner class="h-8" />
	</div>
</template>

<script setup>
import { createResource, Spinner } from 'frappe-ui'
import { computed, inject, provide } from 'vue'
import { teamCache } from '@/data/currentTeam'
import BillingSummary from '../components/billing/BillingSummary.vue'
import PaymentDetails from '../components/billing/PaymentDetails.vue'

const team = inject('team')

const upcomingInvoice = createResource({
	url: 'press.api.billing.upcoming_invoice',
	cache: teamCache('upcomingInvoice'),
	auto: true,
})

const unpaidInvoices = createResource({
	url: 'press.api.billing.get_unpaid_invoices',
	cache: teamCache('unpaidInvoices', team.name),
	auto: true,
})

provide('billing', {
	upcomingInvoice,
	availableCredits: computed(() => upcomingInvoice.data?.available_credits),
	currentBillingAmount: computed(
		() => upcomingInvoice.data?.upcoming_invoice?.total,
	),
	unpaidInvoices,
})
</script>
