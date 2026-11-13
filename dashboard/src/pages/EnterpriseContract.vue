<template>
	<div class="sticky top-0 z-10 shrink-0">
		<Header>
			<Breadcrumbs :items="[{ label: 'Contracts', route: '/contracts' }]" />
			<Button
				v-if="ordering"
				class="ml-auto"
				label="Back to contracts"
				@click="ordering = false"
			/>
			<template v-else-if="contracts.length">
				<Button
					class="ml-auto"
					:class="{ 'mr-2': canOrder }"
					:loading="contract.loading"
					@click="contract.reload()"
				>
					<template #icon><lucide-refresh-ccw class="size-4" /></template>
				</Button>
				<Button v-if="canOrder" variant="solid" @click="ordering = true">
					<template #prefix><lucide-plus class="size-4" /></template>
					Order Contract
				</Button>
			</template>
		</Header>
	</div>

	<div class="w-full px-5" :class="{ 'mx-auto max-w-[72rem]': showForm }">
		<div
			v-if="contract.loading && !contract.data"
			class="flex flex-col items-center gap-3 py-24 text-base text-ink-gray-6"
		>
			<Spinner class="h-6" />
			Loading...
		</div>
		<ErrorMessage
			v-else-if="contract.error"
			class="py-6"
			:message="contract.error"
		/>
		<template v-else-if="contract.data">
			<ContractList v-if="!showForm" class="pt-4" :contracts="contracts" />
			<div
				v-else-if="contract.data.order_blocked"
				class="py-24 text-center text-base text-ink-gray-6"
			>
				{{ contract.data.order_blocked }}
			</div>
			<OrderForm
				v-else-if="contract.data.plans.length"
				:plans="contract.data.plans"
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
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import ContractList from '../components/enterprise-contract/ContractList.vue'
import OrderForm from '../components/enterprise-contract/OrderForm.vue'
import Header from '../components/Header.vue'

const router = useRouter()

const contract = createResource({
	url: 'press.api.enterprise_contract.get',
	auto: true,
})
const contracts = computed(() => contract.data?.contracts || [])
// One order or contract at a time; an unpaid order is paid or cancelled on its page.
const canOrder = computed(
	() =>
		!contract.data?.open_contract &&
		!contract.data?.order_blocked &&
		contract.data?.plans.length > 0,
)
const ordering = ref(false)
const showForm = computed(
	() => contract.data && (ordering.value || !contracts.value.length),
)

function onPlaced(name) {
	router.push({ name: 'Contract', params: { name }, query: { pay: 1 } })
}
</script>
