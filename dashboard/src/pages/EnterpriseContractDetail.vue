<template>
	<Header class="sticky top-0 z-10 bg-surface-white">
		<div class="flex w-full items-center justify-between gap-2">
			<div class="flex items-center gap-2">
				<Breadcrumbs
					:items="[
						{ label: 'Contracts', route: '/contracts' },
						{ label: name, route: `/contracts/${name}` },
					]"
				/>
				<Badge
					v-if="contract"
					:theme="contractHeaderTheme(contract.status)"
					:label="contract.status"
				/>
			</div>
			<div v-if="contract" class="flex items-center gap-2">
				<Button
					v-if="canPay"
					variant="solid"
					:label="payLabel"
					@click="showPay = true"
				/>
				<Dropdown v-if="menu.length" :options="menu">
					<Button>
						<template #icon><LucideEllipsis class="size-4" /></template>
					</Button>
				</Dropdown>
			</div>
		</div>
	</Header>

	<div
		v-if="resource.loading && !resource.data"
		class="flex justify-center py-24"
	>
		<Spinner class="h-6" />
	</div>
	<ErrorMessage
		v-else-if="resource.error"
		class="p-5"
		:message="resource.error"
	/>
	<Tabs v-else-if="contract" v-model="tab" :tabs="tabs">
		<template #tab-item="{ tab: item }">
			<button
				class="flex items-center gap-1.5 whitespace-nowrap py-2.5 text-base text-ink-gray-5 duration-300 ease-in-out hover:text-ink-gray-9 data-[state=active]:text-ink-gray-9"
			>
				<component :is="item.icon" class="size-4" />
				{{ item.label }}
			</button>
		</template>
		<template #tab-panel="{ tab: item }">
			<div class="p-5">
				<ContractOverview
					v-if="item.label === 'Overview'"
					:contract="contract"
					:options="resource.data"
					:can-pay="canPay"
					@pay="showPay = true"
					@updated="resource.reload()"
				/>
				<ContractActivity v-else :steps="contract.activity" />
			</div>
		</template>
	</Tabs>

	<PayDialog
		v-if="contract && canPay"
		v-model="showPay"
		:contract="contract"
		:options="resource.data"
		@card-saved="resource.reload()"
	/>
</template>

<script setup>
import {
	Badge,
	Breadcrumbs,
	Button,
	createResource,
	Dropdown,
	ErrorMessage,
	Spinner,
	Tabs,
} from 'frappe-ui'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import LucideActivity from '~icons/lucide/activity'
import LucideHouse from '~icons/lucide/house'
import ContractActivity from '../components/enterprise-contract/ContractActivity.vue'
import ContractOverview from '../components/enterprise-contract/ContractOverview.vue'
import {
	contractHeaderTheme,
	payActionLabel,
} from '../components/enterprise-contract/format'
import PayDialog from '../components/enterprise-contract/PayDialog.vue'
import Header from '../components/Header.vue'

const props = defineProps({ name: { type: String, required: true } })
const route = useRoute()
const router = useRouter()

const tabs = [
	{ label: 'Overview', icon: LucideHouse },
	{ label: 'Activity', icon: LucideActivity },
]
const tab = ref(0)
const showPay = ref(false)

const resource = createResource({
	url: 'press.api.enterprise_contract.get_contract',
	params: { name: props.name },
	auto: true,
	onSuccess: () => {
		// Opened right after placing an order.
		if (route.query.pay && canPay.value) showPay.value = true
		if (route.query.pay) router.replace({ query: {} })
	},
})
const contract = computed(() => resource.data?.contract)

// The server decides what can be paid with; a bank transfer is paid from the overview.
const canPay = computed(() => Boolean(resource.data?.payment_methods.length))

// A payment left unfinished when the dialog closed shows up as a retry.
watch(showPay, (open) => {
	if (!open) resource.reload()
})

const payLabel = computed(() => payActionLabel(contract.value))

const cancelOrder = createResource({
	url: 'press.api.enterprise_contract.cancel_order',
	onSuccess: ({ message }) => {
		if (message) toast.info(message)
		else toast.success('Order cancelled')
		resource.reload()
	},
	onError: (error) =>
		toast.error(error.messages?.join('\n') || 'Could not cancel the order'),
})

const menu = computed(() => {
	const c = contract.value
	const items = []
	if (c.signed_contract)
		items.push({
			label: 'Download agreement',
			onClick: () => window.open(c.signed_contract, '_blank'),
		})
	if (c.status === 'Awaiting Payment' && !c.transfer_reference)
		items.push({ label: 'Cancel order', onClick: () => cancelOrder.submit() })
	return items
})
</script>
