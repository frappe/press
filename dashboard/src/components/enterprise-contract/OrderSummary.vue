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
				<div class="text-lg font-semibold">{{ money(payToday.total) }}</div>
				<div class="text-base font-medium text-ink-gray-7">
					{{ payToday.gst
							? `${money(payToday.amount)} + ${money(payToday.gst)} GST`
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
			:loadingText="method.loadingText"
			@click="emit('pay')"
		>
			{{ method.button }}
		</Button>
		<p class="text-p-sm text-ink-gray-6">{{ method.note }}</p>
	</div>
</template>

<script setup>
import { Button, ErrorMessage, FormControl } from 'frappe-ui'
import { computed, ref } from 'vue'
import { dayjsLocal as dayjs } from '../../utils/dayjs'
import { currency } from '../../utils/format'

const props = defineProps({
	plan: { type: Object, required: true },
	order: { type: Object, required: true },
	billingName: { type: String, default: '' },
	canPay: { type: Boolean, default: false },
	useCredits: { type: Boolean, default: false },
	lockedUntil: { type: Object, required: true },
	paying: { type: Boolean, default: false },
	error: { type: [String, Object], default: null },
})
const emit = defineEmits(['pay'])

const agreedToTerms = ref(false)
const money = (amount) => currency(amount, props.plan.currency, 0)
const formatDate = (date) => dayjs(date).format('D MMM YYYY')

const methods = {
	credits: {
		label: 'Credits',
		button: 'Pay with Credits',
		loadingText: 'Paying...',
		note: 'The full year is paid from your credit balance. GST was charged when you bought the credits.',
	},
	bank: {
		label: 'Bank transfer (NEFT / RTGS)',
		button: 'Place Order',
		loadingText: 'Placing order...',
		note: 'Next, you will see our bank details to pay by NEFT or RTGS.',
	},
	stripe: {
		label: 'Card via Stripe',
		button: 'Pay on Stripe',
		loadingText: 'Redirecting to Stripe...',
		note: 'You will be redirected to Stripe to complete the payment.',
	},
}

const method = computed(() => {
	if (props.useCredits) return methods.credits
	return props.plan.currency === 'INR' ? methods.bank : methods.stripe
})

// Credits were taxed when they were bought, so paying with them adds no GST.
const payToday = computed(() => {
	const due = props.plan.amount_due
	return props.useCredits ? { ...due, gst: 0, total: due.amount } : due
})

const rows = computed(() => {
	const years = Number(props.order.price_lock_years)
	return [
		{ label: 'Billing Name', value: props.billingName || '—' },
		{ label: 'Applications', value: 'All core apps built by Frappe' },
		{
			label: 'Price Lock',
			value: `${money(props.plan.yearly_price)} / year for ${years} ${years > 1 ? 'years' : 'year'}`,
			hint: `Locked until ${formatDate(props.lockedUntil)}, counted from payment`,
		},
		{ label: 'Payment Method', value: method.value.label },
	]
})
</script>
