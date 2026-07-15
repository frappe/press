<script setup lang="ts">
import { createResource } from 'frappe-ui'
import { computed, defineAsyncComponent } from 'vue'
import { getTeam } from '@/data/team'
import dayjs from '@/utils/dayjs'

withDefaults(defineProps<{ ctxType?: string }>(), { ctxType: 'List Page' })

const AlertAddPaymentMode = defineAsyncComponent(() => import('./AlertAddPaymentMode.vue'))
const AlertCardExpired = defineAsyncComponent(() => import('./AlertCardExpired.vue'))
const AlertAddressDetails = defineAsyncComponent(() => import('./AlertAddressDetails.vue'))
const AlertMandateInfo = defineAsyncComponent(() => import('./AlertMandateInfo.vue'))
const AlertUnpaidInvoices = defineAsyncComponent(() => import('./AlertUnpaidInvoices.vue'))
const AlertCardPaymentFailed = defineAsyncComponent(() => import('./AlertCardPaymentFailed.vue'))
const AlertBudgetThreshold = defineAsyncComponent(() => import('./AlertBudgetThreshold.vue'))
const CustomAlerts = defineAsyncComponent(() => import('./CustomAlerts.vue'))

const team = getTeam()
const isAfterFirstWeek = dayjs().date() > 6

const isCardExpired = computed(() => {
	const expiry = team.doc?.payment_method
	if (!expiry) return false
	if (expiry.expiry_year < dayjs().year()) return true
	return expiry.expiry_year == dayjs().year() && expiry.expiry_month < dayjs().month() + 1
})
const isMandateNotSet = computed(() => !team.doc?.payment_method?.stripe_mandate_id)

const getAmountDue = createResource({ url: 'press.api.billing.total_unpaid_amount', auto: true })
const hasUnpaidInvoices = computed(() => getAmountDue.data)

const getUnpaidInvoices = createResource({
	url: 'press.api.client.get_list',
	params: {
		doctype: 'Invoice',
		fields: ['name', 'stripe_invoice_url', 'stripe_payment_failed', 'stripe_payment_error'],
		filters: { status: 'Unpaid', type: 'Subscription' },
		order_by: 'creation desc',
		limit: 1,
	},
	auto: team.doc?.payment_mode === 'Card' && isAfterFirstWeek,
})
const cardPaymentFailure = computed(() => {
	const invoices = getUnpaidInvoices.data
	if (!invoices) return null
	return (
		invoices.find((inv: any) => {
			if (!inv.stripe_payment_failed || !inv.stripe_invoice_url) return false
			const error = (inv.stripe_payment_error || '').toLowerCase()
			return error.includes('insufficient fund') || error.includes('mandate amount')
		}) || null
	)
})

const getCurrentBillingAmount = createResource({
	url: 'press.api.billing.get_current_billing_amount',
	auto: true,
	cache: 'Current Billing Amount',
})
const displayBudgetAlert = computed(() => {
	if (
		!team.doc?.receive_budget_alerts ||
		!team.doc?.monthly_alert_threshold ||
		team.doc.monthly_alert_threshold <= 0
	)
		return 0
	const difference = getCurrentBillingAmount.data - team.doc.monthly_alert_threshold
	return difference > 0 ? difference.toFixed(2) : 0
})
</script>

<template>
	<template v-if="team.doc">
		<AlertAddPaymentMode class="mb-5" v-if="!team.doc.payment_mode && !team.doc.parent_team" />
		<AlertCardExpired class="mb-5" v-if="isCardExpired && team.doc?.payment_mode == 'Card'" />
		<AlertAddressDetails
			class="mb-5"
			v-if="!team.doc?.billing_details?.name && team.doc.payment_mode"
		/>
		<CustomAlerts :ctx_type="ctxType" />
		<AlertMandateInfo
			class="mb-5"
			v-if="isMandateNotSet && team.doc.currency === 'INR' && team.doc.payment_mode == 'Card'"
		/>
		<AlertUnpaidInvoices
			class="mb-5"
			v-if="hasUnpaidInvoices > 0 && team.doc.payment_mode == 'Prepaid Credits'"
			:amount="hasUnpaidInvoices"
		/>
		<AlertCardPaymentFailed
			class="mb-5"
			v-if="cardPaymentFailure && team.doc.payment_mode == 'Card' && isAfterFirstWeek && !isCardExpired && !isMandateNotSet"
			:errorMessage="cardPaymentFailure.stripe_payment_error"
			:stripeUrl="cardPaymentFailure.stripe_invoice_url"
		/>
		<AlertBudgetThreshold
			class="mb-5"
			v-if="displayBudgetAlert > 0"
			:amount="displayBudgetAlert"
			:currency="team.doc.currency == 'INR' ? '₹' : '$'"
		/>
	</template>
</template>
