<template>
	<div class="rounded-md border">
		<div class="h-12 border-b px-5 py-4">
			<h2 class="text-lg font-medium text-ink-gray-9">Payments</h2>
		</div>
		<div
			v-if="!contract.payments.length"
			class="px-5 py-6 text-base text-ink-gray-6"
		>
			No payments yet
		</div>
		<div
			v-for="payment in contract.payments"
			:key="payment.payment_reference"
			class="flex items-start justify-between gap-4 px-5 py-3 text-base last:pb-5 even:bg-surface-gray-1"
		>
			<div>
				<div class="text-ink-gray-9">
					{{ formatDate(payment.period_start) }}
					–
					{{ formatDate(payment.period_end) }}
				</div>
				<div class="mt-1 text-sm text-ink-gray-6">
					{{ payment.paid_with || 'Paid' }}
					· {{ formatDate(payment.paid_on) }}
				</div>
			</div>
			<div class="text-right">
				<div class="text-ink-gray-9">
					{{ money(payment.amount_paid || payment.amount, contract.currency) }}
				</div>
				<a
					v-if="payment.invoice_pdf"
					class="mt-1 inline-flex items-center gap-1 text-sm text-ink-gray-7 underline"
					:href="payment.invoice_pdf"
					target="_blank"
				>
					{{ payment.frappe_invoice || 'Tax invoice' }}
					<LucideDownload class="size-3.5" />
				</a>
				<div v-else class="mt-1 text-sm text-ink-gray-6">
					{{ payment.frappe_invoice || 'Invoice sent by email' }}
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { formatDate, money } from './format'

defineProps({ contract: { type: Object, required: true } })
</script>
