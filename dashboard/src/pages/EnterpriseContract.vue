<template>
	<div class="sticky top-0 z-10 shrink-0">
		<Header>
			<Breadcrumbs :items="[{ label: 'Contracts', route: '/contracts' }]" />
			<Button
				v-if="ordering"
				label="Back to contracts"
				@click="ordering = false"
			/>
		</Header>
	</div>

	<div
		class="mx-auto w-full px-4 sm:px-5"
		:class="showForm ? 'max-w-[72rem]' : 'max-w-3xl'"
	>
		<div
			v-if="verifyPayment.loading || (contract.loading && !contract.data)"
			class="flex flex-col items-center gap-3 py-24 text-base text-ink-gray-6"
		>
			<Spinner class="h-6" />
			{{ verifyPayment.loading ? 'Confirming your payment...' : 'Loading...' }}
		</div>
		<ErrorMessage
			v-else-if="contract.error || verifyPayment.error"
			class="py-6"
			:message="contract.error || verifyPayment.error"
		/>
		<template v-else-if="contract.data">
			<div v-if="!showForm" class="flex flex-col gap-6 py-8">
				<AwaitingPayment
					v-if="awaiting"
					:contract="current"
					:bank="contract.data.bank_transfer"
					:credit-balance="contract.data.credit_balance"
					@updated="contract.reload()"
				/>
				<ContractList
					v-if="listed.length"
					:contracts="listed"
					:can-order="!current && contract.data.plans.length > 0"
					@new="ordering = true"
				/>
			</div>
			<OrderForm
				v-else-if="contract.data.plans.length"
				:plans="contract.data.plans"
				:credit-balance="contract.data.credit_balance"
				:gst-split="contract.data.gst_split"
				@placed="onPlaced"
				@billing-saved="contract.reload()"
			/>
			<div v-else class="py-24 text-center text-base text-ink-gray-6">
				No Enterprise plan is available right now.
			</div>
		</template>
	</div>
</template>

<script setup>
import {
	Breadcrumbs,
	Button,
	createResource,
	ErrorMessage,
	Spinner,
} from 'frappe-ui'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import AwaitingPayment from '../components/enterprise-contract/AwaitingPayment.vue'
import ContractList from '../components/enterprise-contract/ContractList.vue'
import { isGatewayReturn } from '../components/enterprise-contract/checkout'
import OrderForm from '../components/enterprise-contract/OrderForm.vue'
import Header from '../components/Header.vue'

const route = useRoute()
const router = useRouter()

const contract = createResource({ url: 'press.api.enterprise_contract.get' })
const current = computed(() => contract.data?.contract)
const contracts = computed(() => contract.data?.contracts || [])
const awaiting = computed(() => current.value?.status === 'Awaiting Payment')
// The awaiting order has its own card above the list.
const listed = computed(() =>
	contracts.value.filter((row) => row.status !== 'Awaiting Payment'),
)
const ordering = ref(false)
const showForm = computed(
	() => contract.data && (ordering.value || !contracts.value.length),
)

function onPlaced() {
	ordering.value = false
	contract.reload()
}

const verifyPayment = createResource({
	url: 'press.api.enterprise_contract.verify_payment',
	onSuccess: (verified) => {
		if (verified.status === 'Awaiting Payment')
			toast.error('Payment was not completed')
		else toast.success('Payment received')
		contract.reload()
	},
})

onMounted(() => {
	const query = { ...route.query }
	if (query.payment === 'cancelled')
		toast.info('Payment cancelled. Your order is saved.')
	if (isGatewayReturn(query)) verifyPayment.submit({ params: query })
	else contract.fetch()
	if (Object.keys(query).length) router.replace({ query: {} })
})
</script>
