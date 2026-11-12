<template>
	<div class="grid grid-cols-1 items-start gap-5 lg:grid-cols-2">
		<AlertBanner
			v-if="banner"
			class="col-span-1 lg:col-span-2"
			:type="banner.type"
			:title="banner.title"
		>
			<Button
				v-if="banner.action"
				class="ml-auto"
				variant="outline"
				:label="banner.action"
				@click="emit('pay')"
			/>
		</AlertBanner>

		<div class="col-span-1 rounded-md border lg:col-span-2">
			<div class="grid grid-cols-2 lg:flex lg:*:flex-1">
				<div
					v-for="(card, i) in summary"
					:key="card.label"
					class="p-5"
					:class="[
						i % 2 === 0 ? 'border-r' : '',
						i < 2 ? 'border-b lg:border-b-0' : '',
						i < summary.length - 1 ? 'lg:border-r' : 'lg:border-r-0',
					]"
				>
					<div class="text-base text-ink-gray-7">{{ card.label }}</div>
					<div class="mt-2 text-base text-ink-gray-9">{{ card.value }}</div>
					<div class="mt-1 text-sm text-ink-gray-6">{{ card.hint }}</div>
				</div>
			</div>
		</div>

		<div
			v-if="showBankTransfer"
			class="col-span-1 overflow-hidden rounded-md border lg:col-span-2"
		>
			<div class="border-b px-5 py-3">
				<h2 class="text-lg font-medium text-ink-gray-9">
					Pay by bank transfer
				</h2>
			</div>
			<BankTransfer
				:contract="contract"
				:bank="options.bank_transfer"
				@submitted="emit('updated')"
			/>
		</div>

		<div class="rounded-md border">
			<div class="h-12 border-b px-5 py-4">
				<h2 class="text-lg font-medium text-ink-gray-9">
					Contract Information
				</h2>
			</div>
			<div
				v-for="row in information"
				:key="row.label"
				class="flex items-start px-5 py-3 last:pb-5 even:bg-surface-gray-1"
			>
				<div class="w-1/3 shrink-0 text-base text-ink-gray-6">
					{{ row.label }}
				</div>
				<div class="w-2/3 whitespace-pre-line text-base text-ink-gray-9">
					<a
						v-if="row.link"
						class="inline-flex items-center gap-1 underline"
						:href="row.link"
						target="_blank"
					>
						{{ row.value }}
						<LucideDownload class="size-3.5" />
					</a>
					<template v-else>{{ row.value }}</template>
				</div>
			</div>
		</div>

		<ContractPayments :contract="contract" />
	</div>
</template>

<script setup>
import { Button } from 'frappe-ui'
import { computed } from 'vue'
import { dayjsLocal as dayjs } from '../../utils/dayjs'
import AlertBanner from '../AlertBanner.vue'
import BankTransfer from './BankTransfer.vue'
import ContractPayments from './ContractPayments.vue'
import { formatDate, money } from './format'

const props = defineProps({
	contract: { type: Object, required: true },
	options: { type: Object, required: true },
	canPay: { type: Boolean, default: false },
})
const emit = defineEmits(['pay', 'updated'])

// Payments come newest first. A renewal paid early is the newest, but today is still in
// the year before it.
const latest = computed(() => props.contract.payments[0])
const current = computed(() => {
	const today = dayjs().format('YYYY-MM-DD')
	return (
		props.contract.payments.find(
			(p) => p.period_start <= today && today <= p.period_end,
		) || latest.value
	)
})
const isBank = computed(
	() => props.contract.payment_gateway === 'Bank Transfer',
)
const showBankTransfer = computed(
	() =>
		isBank.value &&
		props.contract.payment_due &&
		// While a UTR is checked, the banner says so and the bank details are not needed.
		!props.contract.transfer_reference &&
		props.options.bank_transfer &&
		!props.options.payment_blocked,
)

const banner = computed(() => {
	const c = props.contract
	const total = money(c.amount_due.total, c.currency)
	if (c.status === 'Cancelled')
		return { type: 'general', title: 'This order was cancelled.' }
	if (c.payment_due && props.options.payment_blocked)
		return { type: 'warning', title: props.options.payment_blocked }
	// Staff acting in the team see why there is no Pay button.
	if (
		c.payment_due &&
		!isBank.value &&
		!props.canPay &&
		props.options.card_blocked
	)
		return { type: 'warning', title: props.options.card_blocked }
	if (c.transfer_reference)
		return {
			type: 'info',
			title: `We are verifying your bank transfer (UTR ${c.transfer_reference}). This usually takes 1–2 working days.`,
		}
	if (c.status === 'Awaiting Payment')
		return {
			type: 'info',
			title: isBank.value
				? `Your order is saved. Transfer <b>${total}</b> to the bank account below, then enter the UTR.`
				: `Your order is saved. Pay <b>${total}</b> to start your contract.`,
			action: props.canPay ? 'Pay now' : null,
		}
	if (c.payment_due)
		return {
			type: 'warning',
			title: `Your paid year ends on ${formatDate(latest.value.period_end)}. Renew for <b>${total}</b> to keep your warranty.`,
			action: props.canPay ? 'Renew' : null,
		}
	if (c.status === 'Pending Signature')
		return {
			type: 'info',
			title:
				'Payment received. Frappe is signing your agreement, and will email you the signed copy.',
		}
	return null
})

const summary = computed(() => {
	const c = props.contract
	const paid = current.value
	return [
		{
			label: 'Plan',
			value: `${c.plan_title}`,
			hint: `${money(c.yearly_price, c.currency)} / year, excluding taxes`,
		},
		{
			label: 'Current period',
			value: paid
				? `${formatDate(paid.period_start)} – ${formatDate(paid.period_end)}`
				: 'Starts on payment',
			hint: !paid
				? 'One year from the day you pay'
				: paid === latest.value
					? `Contract started ${formatDate(c.start_date)}`
					: `Renewed, paid until ${formatDate(latest.value.period_end)}`,
		},
		{
			label: 'Price lock',
			value: paid
				? `Until ${formatDate(c.price_locked_until)}`
				: `${c.price_lock_years} year${c.price_lock_years > 1 ? 's' : ''}`,
			hint: `Renewals in this period keep ${money(c.yearly_price, c.currency)} / year`,
		},
		{
			label: 'Next renewal',
			value: paid ? formatDate(c.next_renewal.date) : '—',
			hint: paid
				? `${money(c.next_renewal.amount, c.currency)}, opens ${formatDate(c.renewal_opens_on)}`
				: 'After the first year',
		},
	]
})

const information = computed(() => {
	const c = props.contract
	const contact = [c.contact_person, c.designation].filter(Boolean).join(', ')
	return [
		{ label: 'Contract', value: c.name },
		{
			label: 'Covers',
			value: c.coverage.join('\n') || 'All core apps built by Frappe',
		},
		{ label: 'Legal entities', value: c.legal_entities_covered || '—' },
		{ label: 'Billing name', value: c.billing_name || '—' },
		{ label: 'Billing email', value: c.billing_email },
		{ label: 'Contact', value: contact || '—' },
		{ label: 'Billing partner', value: c.billing_partner || '—' },
		c.signed_contract
			? {
					label: 'Agreement',
					value: `Signed ${formatDate(c.agreement_date)}`,
					link: c.signed_contract,
				}
			: { label: 'Agreement', value: 'Frappe signs it after payment' },
	]
})
</script>
