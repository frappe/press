<template>
	<div
		class="flex flex-col rounded-lg text-base text-ink-gray-9 shadow dark:border"
	>
		<div class="flex items-start justify-between gap-4 px-4 py-3">
			<div class="flex flex-col gap-1.5">
				<div class="text-lg font-semibold">{{ contract.plan_title }} plan</div>
				<div class="text-ink-gray-7">
					{{ contract.billing_name }}
					· {{ contract.name }}
				</div>
			</div>
			<div class="flex items-center gap-2">
				<Button
					v-if="!contract.transfer_reference"
					label="Cancel order"
					variant="ghost"
					:loading="cancelOrder.loading"
					@click="cancelOrder.submit()"
				/>
				<Badge size="lg" theme="orange" label="Awaiting payment" />
			</div>
		</div>
		<ContractProgress class="px-4 pb-4 pt-1" :status="contract.status" />

		<div
			v-if="canUseCredits"
			class="m-1.5 flex flex-wrap items-center justify-between gap-3 rounded-lg bg-surface-gray-1 px-2.5 py-2"
		>
			<div class="flex items-center gap-2 text-ink-gray-8">
				<LucideWallet class="h-4 w-4" />
				<span>
					Or pay
					<span class="font-medium text-ink-gray-9">{{ creditPrice }}</span>
					from your credit balance{{ contract.currency === 'INR' ? ', with no GST' : '' }}.
				</span>
			</div>
			<Button
				label="Pay with Credits"
				:loading="payWithCredits.loading"
				@click="payWithCredits.submit()"
			/>
		</div>

		<BankTransfer
			v-if="contract.payment_gateway === 'Bank Transfer'"
			:contract="contract"
			:bank="bank"
			@submitted="emit('updated')"
		/>
		<div
			v-else
			class="m-1.5 flex flex-wrap items-center justify-between gap-3 rounded-lg bg-surface-gray-1 px-2.5 py-2"
		>
			<div class="flex items-center gap-2 text-ink-gray-8">
				<LucideCreditCard class="h-4 w-4" />
				<span>
					Your order is saved. Pay
					<span class="font-medium text-ink-gray-9">{{ total }}</span>
					on Stripe to place it.
				</span>
			</div>
			<Button
				variant="solid"
				:loading="redirecting"
				loadingText="Redirecting to Stripe..."
				@click="payNow"
			>
				Pay {{ total }}
			</Button>
		</div>
		<ErrorMessage
			class="px-4 pb-3"
			:message="pay.error || cancelOrder.error || payWithCredits.error"
		/>
	</div>
</template>

<script setup>
import { Badge, Button, createResource, ErrorMessage } from 'frappe-ui'
import { computed, ref } from 'vue'
import { getTeam } from '../../data/team'
import { currency } from '../../utils/format'
import BankTransfer from './BankTransfer.vue'
import ContractProgress from './ContractProgress.vue'
import { contractsReturnUrl } from './checkout'

const props = defineProps({
	contract: { type: Object, required: true },
	bank: { type: Object, default: null },
})
const emit = defineEmits(['updated'])

const team = getTeam()
const redirecting = ref(false)
const creditPrice = computed(() =>
	currency(props.contract.amount_due.amount, props.contract.currency, 0),
)
// Hidden once a bank transfer is on its way, so the year is not paid twice.
const canUseCredits = computed(
	() =>
		!props.contract.transfer_reference &&
		(team.doc.balance || 0) >= props.contract.amount_due.amount,
)

const payWithCredits = createResource({
	url: 'press.api.enterprise_contract.pay_with_credits',
	onSuccess: () => {
		team.reload()
		emit('updated')
	},
})
const total = computed(() =>
	currency(props.contract.amount_due.total, props.contract.currency, 0),
)

const pay = createResource({
	url: 'press.api.enterprise_contract.pay',
	makeParams: () => ({ return_url: contractsReturnUrl() }),
	onSuccess: ({ checkout_url }) => window.location.assign(checkout_url),
	onError: () => (redirecting.value = false),
})

const cancelOrder = createResource({
	url: 'press.api.enterprise_contract.cancel_order',
	onSuccess: () => emit('updated'),
})

function payNow() {
	redirecting.value = true
	pay.submit()
}
</script>
