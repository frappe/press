<template>
	<ol class="divide-y">
		<li class="flex gap-4 px-5 py-4">
			<StepMarker :number="1" :state="submitted ? 'done' : 'current'" />
			<div class="flex min-w-0 flex-1 flex-col gap-3">
				<div>
					<div class="text-base font-medium text-ink-gray-9">
						Transfer {{ money(due.total) }} by NEFT or RTGS
					</div>
					<div class="mt-1 text-base text-ink-gray-6">
						{{ submitted ? transferredTo : breakdown }}
					</div>
				</div>
				<template v-if="!submitted">
					<dl
						class="grid grid-cols-[9rem_1fr] items-center gap-y-2 rounded-md bg-surface-gray-1 px-4 py-3 text-base"
					>
						<template v-for="row in bankRows" :key="row.label">
							<dt class="text-ink-gray-6">{{ row.label }}</dt>
							<dd class="flex min-w-0 items-center gap-1.5 text-ink-gray-9">
								<span
									class="truncate"
									:class="{ 'font-mono': row.mono, 'font-medium': row.strong }"
								>
									{{ row.value }}
								</span>
								<CopyBtn
									v-if="row.copy"
									:text="row.copy"
									class="text-ink-gray-6"
								/>
							</dd>
						</template>
					</dl>
					<div
						class="flex items-center gap-2 rounded-md border border-dashed px-3 py-2 text-base text-ink-gray-8"
					>
						<LucideInfo class="size-4 shrink-0 text-ink-gray-6" />
						<span>
							Write
							<span class="rounded bg-surface-gray-2 px-1.5 font-mono"
								>{{ contract.name }}</span
							>
							in the transfer remarks, so we can match your payment.
						</span>
						<CopyBtn
							:text="contract.name"
							class="ml-auto shrink-0 text-ink-gray-6"
						/>
					</div>
				</template>
			</div>
		</li>

		<li class="flex gap-4 px-5 py-4">
			<StepMarker :number="2" :state="submitted ? 'done' : 'current'" />
			<div class="flex min-w-0 flex-1 flex-col gap-3">
				<div>
					<div class="text-base font-medium text-ink-gray-9">
						{{ utrStepTitle }}
					</div>
					<div class="mt-1 text-base text-ink-gray-6">
						<span v-if="submitted" class="font-mono"
							>{{ contract.transfer_reference }}</span
						>
						<template v-else>
							The UTR is the reference number your bank shows on the transfer
							confirmation (12 to 22 letters and digits). We use it to find your
							payment.
						</template>
					</div>
				</div>
				<form
					v-if="!submitted"
					class="flex flex-wrap items-end gap-2"
					@submit.prevent="submitReference.submit()"
				>
					<FormControl
						v-model="utr"
						class="min-w-60 flex-1"
						label="UTR number"
						placeholder="e.g. 412345678901"
					/>
					<Button
						type="submit"
						variant="solid"
						label="Submit UTR"
						:loading="submitReference.loading"
					/>
				</form>
				<ErrorMessage :message="submitReference.error" />
			</div>
		</li>

		<li class="flex gap-4 px-5 py-4">
			<StepMarker :number="3" :state="submitted ? 'current' : 'next'" />
			<div>
				<div
					class="flex items-center gap-2 text-base font-medium"
					:class="submitted ? 'text-ink-gray-9' : 'text-ink-gray-7'"
				>
					{{ verifyStep.title }}
					<Badge v-if="submitted" theme="blue" label="In progress" />
				</div>
				<div class="mt-1 text-base text-ink-gray-6">
					{{ verifyStep.description }}
				</div>
			</div>
		</li>
	</ol>
</template>

<script setup>
import {
	Badge,
	Button,
	createResource,
	ErrorMessage,
	FormControl,
} from 'frappe-ui'
import { computed, ref } from 'vue'
import { currency } from '../../utils/format'
import CopyBtn from '../utils/CopyBtn.vue'
import { gstLines } from './format'
import StepMarker from './StepMarker.vue'

const props = defineProps({
	contract: { type: Object, required: true },
	bank: { type: Object, required: true },
})
const emit = defineEmits(['submitted'])

const utr = ref('')
const money = (amount) => currency(amount, props.contract.currency, 2)
const due = computed(() => props.contract.amount_due)
const submitted = computed(() => Boolean(props.contract.transfer_reference))

// Banks show the UTR on the transfer confirmation; Frappe matches it on the statement.
const submitReference = createResource({
	url: 'press.api.enterprise_contract.submit_transfer_reference',
	makeParams: () => ({ reference: utr.value }),
	onSuccess: (contract) => emit('submitted', contract),
})

const breakdown = computed(() =>
	[
		`Plan ${money(due.value.amount)}`,
		...gstLines(due.value.gst, props.contract.gst_split).map(
			(line) => `${line.label} ${money(line.amount)}`,
		),
	].join(' + '),
)

const transferredTo = computed(
	() =>
		`Sent to ${props.bank.bank_account_name} (${props.bank.bank_ifsc_code})`,
)

const utrStepTitle = computed(() =>
	submitted.value
		? 'UTR submitted'
		: 'After the transfer, enter its UTR number',
)

// The first payment starts the contract and Frappe signs it; a renewal adds a year.
const verifyStep = computed(() =>
	props.contract.payments.length
		? {
				title: 'We verify the payment and add your next year',
				description: 'Usually 1 to 2 working days.',
			}
		: {
				title: 'We verify the payment and sign the agreement',
				description:
					'We confirm the payment in 1 to 2 working days, then sign the agreement. You can download it from this page.',
			},
)

const bankRows = computed(() => [
	{
		label: 'Amount',
		value: money(due.value.total),
		copy: String(due.value.total),
		strong: true,
	},
	{
		label: 'Account name',
		value: props.bank.bank_account_name,
		copy: props.bank.bank_account_name,
	},
	{
		label: 'Account number',
		value: props.bank.bank_account_number,
		copy: props.bank.bank_account_number,
		mono: true,
	},
	{
		label: 'IFSC code',
		value: props.bank.bank_ifsc_code,
		copy: props.bank.bank_ifsc_code,
		mono: true,
	},
	{
		label: 'Bank',
		value: [props.bank.bank_name, props.bank.bank_branch]
			.filter(Boolean)
			.join(', '),
	},
])
</script>
