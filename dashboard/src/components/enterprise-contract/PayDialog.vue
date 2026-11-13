<template>
	<Dialog v-model="show" :options="{ title }">
		<template #body-content>
			<div class="space-y-4 text-base">
				<div class="text-ink-gray-7">{{ subtitle }}</div>

				<div class="space-y-2">
					<button
						v-for="m in methods"
						:key="m.key"
						class="flex w-full items-start gap-3 rounded-md border px-3 py-2.5 text-left"
						:class="
							selected === m.key
								? 'border-outline-gray-5 ring-1 ring-gray-900'
								: 'border-outline-gray-3 hover:bg-surface-gray-1'
						"
						@click="selected = m.key"
					>
						<component
							:is="m.icon"
							class="mt-0.5 size-4 shrink-0 text-ink-gray-7"
						/>
						<div class="flex-1">
							<div class="font-medium text-ink-gray-9">{{ m.label }}</div>
							<div class="mt-0.5 text-p-sm text-ink-gray-6">{{ m.hint }}</div>
						</div>
						<div class="text-ink-gray-9">{{ m.amount }}</div>
					</button>
				</div>

				<label v-show="selected === 'new_card'" class="block">
					<span class="text-sm text-ink-gray-6">Credit or debit card</span>
					<div
						ref="cardElementRef"
						class="form-input mt-1.5 block w-full py-2 pl-3"
					/>
				</label>

				<div v-if="options.card_blocked" class="text-p-sm text-ink-gray-6">
					{{ options.card_blocked }}
				</div>
				<ErrorMessage :message="errorMessage || pay.error || confirm.error" />
			</div>
		</template>
		<template #actions>
			<Button
				class="w-full"
				variant="solid"
				:disabled="!selected"
				:loading="busy"
				:loadingText="'Paying...'"
				@click="onPay"
			>
				{{ selected === 'save_card' ? 'Add card' : `Pay ${payAmount}` }}
			</Button>
		</template>
	</Dialog>

	<AddCardDialog
		v-if="showAddCard"
		v-model="showAddCard"
		@success="onCardSaved"
	/>
</template>

<script setup>
import { loadStripe } from '@stripe/stripe-js'
import { Button, createResource, Dialog, ErrorMessage } from 'frappe-ui'
import { computed, nextTick, ref, watch } from 'vue'
import { toast } from 'vue-sonner'
import LucideCreditCard from '~icons/lucide/credit-card'
import LucidePlus from '~icons/lucide/plus'
import LucideWallet from '~icons/lucide/wallet'
import { getStripeErrorMessage } from '../../utils/stripeError'
import AddCardDialog from '../billing/AddCardDialog.vue'
import { formatDate, money, payActionLabel } from './format'

const props = defineProps({
	contract: { type: Object, required: true },
	options: { type: Object, required: true },
})
const emit = defineEmits(['cardSaved'])
const show = defineModel({ type: Boolean })

const selected = ref(null)
const showAddCard = ref(false)
const errorMessage = ref(null)
const confirming = ref(false)
const cardElementRef = ref(null)
let stripe = null
let cardElement = null

const isRenewal = computed(() => props.contract.payments.length > 0)
const title = computed(() => payActionLabel(props.contract))
const subtitle = computed(() => {
	const start = formatDate(props.contract.next_renewal.date)
	return isRenewal.value
		? `${props.contract.plan_title} plan, one year from ${start}.`
		: `${props.contract.plan_title} plan, one year from the day you pay.`
})

const cardTotal = computed(() =>
	money(props.contract.amount_due.total, props.contract.currency),
)
const creditTotal = computed(() =>
	money(props.contract.amount_due_with_credits.total, props.contract.currency),
)
const payAmount = computed(() =>
	selected.value === 'credits' ? creditTotal.value : cardTotal.value,
)

// Shown in the order the server lists them, which is also the rule for what is offered.
const methods = computed(() =>
	props.options.payment_methods.map((key) => ({ key, ...methodDetails(key) })),
)

function methodDetails(key) {
	const { options, contract } = props
	return {
		saved_card: {
			icon: LucideCreditCard,
			label: options.saved_card?.label,
			hint: "Your team's default card. It also pays your monthly Frappe Cloud invoices.",
			amount: cardTotal.value,
		},
		save_card: {
			icon: LucidePlus,
			label: options.saved_card ? 'Save a different card' : 'Save a card',
			hint: "The card becomes your team's default payment method. Your monthly Frappe Cloud invoices will be charged to it too, and you can use it to renew this contract.",
		},
		new_card: {
			icon: LucideCreditCard,
			label: 'Pay once with a card',
			hint: 'Charges the card for this payment only. The card is not saved, and your monthly invoices are not changed.',
			amount: cardTotal.value,
		},
		credits: {
			icon: LucideWallet,
			label: 'Credits',
			hint: `Balance ${money(options.credit_balance, contract.currency)}.${contract.currency === 'INR' ? ' No GST, it was charged when you bought the credits.' : ''}`,
			amount: creditTotal.value,
		},
	}[key]
}

watch(
	[show, methods],
	() => {
		if (show.value && !methods.value.some((m) => m.key === selected.value))
			selected.value = methods.value[0]?.key ?? null
	},
	{ immediate: true },
)

// The dialog's body is removed on close, and the card field with it. Start clean on the
// next open, so that a payment can be retried.
watch(show, (open) => {
	if (open) return
	cardElement?.destroy()
	cardElement = null
	selected.value = null
	errorMessage.value = null
})

watch(selected, async (key) => {
	errorMessage.value = null
	if (key === 'new_card' && !cardElement) await mountCardElement()
})

async function getStripe() {
	stripe ??= await loadStripe(props.options.publishable_key)
	return stripe
}

async function mountCardElement() {
	const elements = (await getStripe()).elements()
	cardElement = elements.create('card', {
		hidePostalCode: true,
		style: {
			base: {
				color: '#171717',
				fontSize: '13px',
				'::placeholder': { color: '#C7C7C7' },
			},
		},
	})
	await nextTick()
	cardElement.mount(cardElementRef.value)
	cardElement.on('change', (event) => {
		errorMessage.value = event.error?.message || null
	})
}

const pay = createResource({
	url: 'press.api.enterprise_contract.pay',
	makeParams: () => ({ method: selected.value }),
	onSuccess: ({ payment, message }) => {
		if (message) return done(message)
		if (!payment || payment.status === 'succeeded') return done()
		completeCardPayment(payment)
	},
})

// Records the payment right away; the Stripe webhook would also record it.
const confirm = createResource({
	url: 'press.api.enterprise_contract.confirm_card_payment',
	onSuccess: (contract) => {
		confirming.value = false
		if (contract.payment_due && contract.status === props.contract.status) {
			errorMessage.value =
				'We have not received the payment yet. Please refresh in a minute.'
			return
		}
		done()
	},
	onError: () => (confirming.value = false),
})

// A saved card may need 3-D Secure; a card paid once is entered here.
async function completeCardPayment({ client_secret }) {
	confirming.value = true
	const data =
		selected.value === 'new_card'
			? { payment_method: { card: cardElement } }
			: undefined
	const { error } = await (await getStripe()).confirmCardPayment(
		client_secret,
		data,
	)
	if (error) {
		confirming.value = false
		errorMessage.value = getStripeErrorMessage(error)
		return
	}
	confirm.submit()
}

function onPay() {
	errorMessage.value = null
	if (selected.value === 'save_card') showAddCard.value = true
	else pay.submit()
}

function onCardSaved() {
	showAddCard.value = false
	emit('cardSaved')
	selected.value = 'saved_card'
}

function done(message) {
	if (message) toast.info(message)
	else toast.success(isRenewal.value ? 'Contract renewed' : 'Payment received')
	// Closing reloads the contract page.
	show.value = false
}

const busy = computed(() => pay.loading || confirming.value || confirm.loading)
</script>
