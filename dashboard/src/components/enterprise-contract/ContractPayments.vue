<template>
	<div
		class="flex flex-col rounded-lg text-base text-ink-gray-9 shadow dark:border"
	>
		<div class="px-4 py-3 text-lg font-semibold">Payments</div>
		<div
			class="grid grid-cols-3 border-y bg-surface-gray-1 px-4 py-2 text-sm text-ink-gray-6"
		>
			<span>Period</span>
			<span>Amount paid</span>
			<span class="text-right">frappe.io invoice</span>
		</div>
		<div class="divide-y">
			<div
				v-for="payment in contract.payments"
				:key="payment.payment_reference"
				class="grid grid-cols-3 items-center px-4 py-3"
			>
				<div>
					<div>
						{{ formatDate(payment.period_start) }}
						– {{ formatDate(payment.period_end) }}
					</div>
					<div class="text-sm text-ink-gray-6">
						Paid {{ formatDate(payment.paid_on) }}
					</div>
				</div>
				<div>
					<div>{{ money(payment.amount_paid || payment.amount) }}</div>
					<div v-if="payment.gst" class="text-sm text-ink-gray-6">
						incl. {{ money(payment.gst) }} GST
					</div>
				</div>
				<div class="flex justify-end">
					<Button
						v-if="payment.invoice_pdf"
						:label="payment.frappe_invoice || 'Invoice'"
						:link="payment.invoice_pdf"
					>
						<template #prefix><LucideDownload class="h-4 w-4" /></template>
					</Button>
					<span v-else-if="payment.frappe_invoice" class="text-ink-gray-8">
						{{ payment.frappe_invoice }}
					</span>
					<Tooltip
						v-else
						text="The invoice shows here once it syncs from frappe.io"
					>
						<Badge theme="gray" label="Syncing" />
					</Tooltip>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { Badge, Button, Tooltip } from 'frappe-ui'
import { dayjsLocal as dayjs } from '../../utils/dayjs'
import { currency } from '../../utils/format'

const props = defineProps({ contract: { type: Object, required: true } })

const money = (amount) => currency(amount, props.contract.currency, 0)
const formatDate = (date) => dayjs(date).format('D MMM YYYY')
</script>
