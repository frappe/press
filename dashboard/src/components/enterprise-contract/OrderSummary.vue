<template>
	<div
		class="h-fit w-full space-y-4 rounded border border-outline-gray-3 bg-surface-white p-6 text-ink-gray-9 lg:sticky lg:top-[4.5rem] lg:w-[25rem]"
	>
		<h2 class="text-md font-semibold">Summary</h2>

		<div v-for="row in rows" :key="row.label" class="flex flex-col space-y-1">
			<div class="text-base text-ink-gray-7">{{ row.label }}</div>
			<div class="text-base font-medium">{{ row.value }}</div>
			<div v-if="row.hint" class="text-base text-ink-gray-7">
				{{ row.hint }}
			</div>
		</div>

		<hr class="mt-2 h-2" />

		<div class="flex flex-col space-y-2">
			<div class="text-base text-ink-gray-7">Pay Today</div>
			<div class="flex flex-col space-y-1">
				<div class="text-lg font-semibold">
					{{ money(payToday.total, plan.currency) }}
				</div>
				<div class="text-base font-medium text-ink-gray-7">
					{{ payToday.gst
							? `${money(payToday.amount, plan.currency)} + ${gstText(payToday.gst, gstSplit, plan.currency)}`
							: 'for the first year' }}
				</div>
			</div>
		</div>

		<FormControl
			v-model="agreedToTerms"
			type="checkbox"
			size="sm"
			variant="subtle"
			label="I agree to the Frappe Enterprise terms. Frappe signs and dates the agreement after payment."
		/>
		<ErrorMessage class="my-2" :message="error" />

		<Button
			variant="solid"
			size="md"
			class="w-full"
			:disabled="!canPay || !agreedToTerms"
			:loading="paying"
			loadingText="Placing order..."
			@click="emit('pay')"
		>
			Place Order
		</Button>
		<p class="text-p-sm text-ink-gray-6">{{ method.note }}</p>
	</div>
</template>

<script setup>
import { Button, ErrorMessage, FormControl } from 'frappe-ui'
import { computed, ref } from 'vue'
import { formatDate, gstText, money } from './format'

const props = defineProps({
	plan: { type: Object, required: true },
	order: { type: Object, required: true },
	billingName: { type: String, default: '' },
	gstSplit: { type: String, default: null },
	canPay: { type: Boolean, default: false },
	lockedUntil: { type: Object, required: true },
	paying: { type: Boolean, default: false },
	error: { type: [String, Object], default: null },
})
const emit = defineEmits(['pay'])

const agreedToTerms = ref(false)

// Paid on the contract page once the order is placed.
const method = computed(() =>
	props.plan.currency === 'INR'
		? {
				label: 'Bank transfer (NEFT / RTGS) or credits',
				note: 'Next, you will see our bank details. You can also pay from your credit balance.',
			}
		: {
				label: 'Card or credits',
				note: 'Next, pay with your saved card, a new card, or your credit balance.',
			},
)

const payToday = computed(() => props.plan.amount_due)

const rows = computed(() => {
	const years = Number(props.order.price_lock_years)
	return [
		{ label: 'Billing Name', value: props.billingName || '—' },
		{ label: 'Applications', value: 'All core apps built by Frappe' },
		{
			label: 'Price Lock',
			value: `${money(props.plan.yearly_price, props.plan.currency)} / year for ${years} ${years > 1 ? 'years' : 'year'}`,
			hint: `Locked until ${formatDate(props.lockedUntil)}, counted from payment`,
		},
		{ label: 'Payment Method', value: method.value.label },
	]
})
</script>
