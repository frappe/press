<template>
	<div class="flex flex-col">
		<div
			class="grid grid-cols-1 divide-y border-y sm:grid-cols-3 sm:divide-x sm:divide-y-0"
		>
			<div
				v-for="line in amountLines"
				:key="line.label"
				class="flex flex-col gap-1 px-4 py-3"
			>
				<div class="text-sm text-ink-gray-6">{{ line.label }}</div>
				<div class="flex items-center gap-1.5 font-medium text-ink-gray-9">
					{{ line.value }}
					<CopyBtn v-if="line.copy" :text="line.copy" class="text-ink-gray-6" />
				</div>
			</div>
		</div>

		<div class="px-4 pt-4 text-sm text-ink-gray-6">
			Transfer by NEFT or RTGS to
		</div>
		<dl class="grid grid-cols-[10rem_1fr] gap-y-2 px-4 py-3">
			<template v-for="row in bankRows" :key="row.label">
				<dt class="text-ink-gray-6">{{ row.label }}</dt>
				<dd class="flex items-center gap-1.5 text-ink-gray-9">
					<span :class="{ 'font-mono': row.mono }">{{ row.value }}</span>
					<CopyBtn v-if="row.value" :text="row.value" class="text-ink-gray-6" />
				</dd>
			</template>
		</dl>

		<div class="m-1.5 rounded-lg bg-surface-gray-1 px-2.5 py-2">
			<div
				v-if="contract.transfer_reference"
				class="flex h-7 items-center gap-2 text-ink-gray-8"
			>
				<LucideHourglass class="h-4 w-4 shrink-0" />
				<span>
					We are verifying your transfer (UTR
					<span class="font-mono">{{ contract.transfer_reference }}</span>).
					This usually takes 1–2 working days.
				</span>
			</div>
			<div v-else class="flex flex-wrap items-end gap-2">
				<FormControl
					v-model="utr"
					class="min-w-60 flex-1"
					label="UTR number"
					placeholder="From your bank's transfer confirmation"
				/>
				<Button
					variant="solid"
					label="I have made the transfer"
					:disabled="!utr"
					:loading="submitReference.loading"
					@click="submitReference.submit()"
				/>
			</div>
			<ErrorMessage class="mt-2" :message="submitReference.error" />
		</div>
	</div>
</template>

<script setup>
import { Button, createResource, ErrorMessage, FormControl } from 'frappe-ui'
import { computed, ref } from 'vue'
import { currency } from '../../utils/format'
import CopyBtn from '../utils/CopyBtn.vue'

const props = defineProps({
	contract: { type: Object, required: true },
	bank: { type: Object, required: true },
})
const emit = defineEmits(['submitted'])

const utr = ref('')
const money = (amount) => currency(amount, props.contract.currency, 2)

// Banks show the UTR on the transfer confirmation; Frappe matches it on the statement.
const submitReference = createResource({
	url: 'press.api.enterprise_contract.submit_transfer_reference',
	makeParams: () => ({ reference: utr.value }),
	onSuccess: (contract) => emit('submitted', contract),
})

const amountLines = computed(() => {
	const due = props.contract.amount_due
	return [
		{ label: 'Plan price', value: money(due.amount) },
		{ label: 'GST', value: money(due.gst) },
		{
			label: 'Amount to transfer',
			value: money(due.total),
			copy: String(due.total),
		},
	]
})

const bankRows = computed(() => [
	{ label: 'Account name', value: props.bank.bank_account_name },
	{
		label: 'Account number',
		value: props.bank.bank_account_number,
		mono: true,
	},
	{ label: 'IFSC code', value: props.bank.bank_ifsc_code, mono: true },
	{
		label: 'Bank',
		value: [props.bank.bank_name, props.bank.bank_branch]
			.filter(Boolean)
			.join(', '),
	},
	{ label: 'Remarks', value: props.contract.name, mono: true },
])
</script>
