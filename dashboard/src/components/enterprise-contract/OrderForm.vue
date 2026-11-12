<template>
	<div
		class="flex w-full flex-col gap-8 pb-[50vh] pt-4 sm:pt-8 lg:flex-row lg:justify-center lg:gap-[60px]"
	>
		<div class="w-full space-y-8 lg:min-w-[42rem] lg:max-w-[42rem]">
			<div v-if="plans.length > 1">
				<h2 class="text-base font-semibold leading-6 text-ink-gray-9">
					Select Plan
				</h2>
				<div class="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-3">
					<button
						v-for="p in plans"
						:key="p.name"
						:class="tileClass(order.plan === p.name)"
						@click="selectPlan(p)"
					>
						<div class="px-4 py-3">
							<div class="text-lg text-ink-gray-9">{{ p.title }}</div>
							<div class="text-sm text-ink-gray-6">
								{{ money(p.yearly_price, p.currency) }}
								/ year
							</div>
						</div>
					</button>
				</div>
			</div>

			<div>
				<div class="flex items-center justify-between">
					<h2 class="text-base font-semibold leading-6 text-ink-gray-9">
						{{ plan.title }}
						Plan
					</h2>
					<span class="text-base text-ink-gray-7">
						<span class="font-medium text-ink-gray-9">{{ price }}</span>
						/ year
					</span>
				</div>
				<div
					class="mt-2 rounded-md border border-outline-gray-3 p-4 text-base text-ink-gray-9"
				>
					<div v-if="plan.description" class="mb-4">{{ plan.description }}</div>
					<div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
						<div
							v-for="item in plan.coverage"
							:key="item"
							class="flex items-center gap-2 text-ink-gray-8"
						>
							<LucideCheck class="h-4 w-4 shrink-0 text-ink-gray-6" />
							{{ item }}
						</div>
					</div>
				</div>
			</div>

			<div>
				<h2 class="text-base font-semibold leading-6 text-ink-gray-9">
					Customer Details
				</h2>
				<CustomerFields class="mt-2" :order="order" />
			</div>

			<div>
				<h2 class="text-base font-semibold leading-6 text-ink-gray-9">
					Billing Details
				</h2>
				<BillingDetailsCard class="mt-2" @saved="emit('billingSaved')" />
			</div>

			<div>
				<div class="flex items-center justify-between">
					<h2 class="text-base font-semibold leading-6 text-ink-gray-9">
						Select Price Lock Period
					</h2>
					<Tooltip
						text="You pay one year at a time. Renewals inside the price lock period use today's price, even if the list price goes up."
					>
						<span class="flex items-center gap-1.5 text-base text-ink-gray-7">
							<LucideCircleHelp class="h-4 w-4" />
							How it works
						</span>
					</Tooltip>
				</div>
				<div class="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-3">
					<button
						v-for="years in plan.price_lock_years"
						:key="years"
						:class="tileClass(Number(order.price_lock_years) === years)"
						@click="order.price_lock_years = years"
					>
						<div class="px-4 py-3">
							<div class="text-lg text-ink-gray-9">
								{{ years }} {{ years > 1 ? 'years' : 'year' }}
							</div>
							<div class="text-sm text-ink-gray-6">{{ price }} / year</div>
						</div>
						<div class="border-t px-4 py-3 text-sm text-ink-gray-7">
							Locked until {{ formatDate(lockedUntil(years)) }}
						</div>
					</button>
				</div>
				<p class="mt-2 text-p-sm text-ink-gray-6">
					The contract starts on the day we receive your payment.
				</p>
			</div>

			<div>
				<h2 class="text-base font-semibold leading-6 text-ink-gray-9">
					Billing Partner
					<span class="font-normal text-ink-gray-6">(optional)</span>
				</h2>
				<FormControl
					v-model="order.billing_partner"
					class="mt-2"
					placeholder="Name of the Frappe partner who bills you"
				/>
			</div>
		</div>

		<OrderSummary
			:plan="plan"
			:order="order"
			:billing-name="team.doc.billing_details?.billing_name"
			:gst-split="gstSplit"
			:can-pay="hasBillingAddress"
			:locked-until="lockedUntil(Number(order.price_lock_years))"
			:paying="paying"
			:error="submit.error"
			@pay="pay"
		/>
	</div>
</template>

<script setup>
import { createResource, FormControl, Tooltip } from 'frappe-ui'
import { computed, reactive, ref } from 'vue'
import { toast } from 'vue-sonner'
import { getTeam } from '../../data/team'
import { dayjsLocal as dayjs } from '../../utils/dayjs'
import BillingDetailsCard from './BillingDetailsCard.vue'
import CustomerFields from './CustomerFields.vue'
import { formatDate, money } from './format'
import OrderSummary from './OrderSummary.vue'

const props = defineProps({
	plans: { type: Array, required: true },
	gstSplit: { type: String, default: null },
})
const emit = defineEmits(['placed', 'billingSaved'])

const team = getTeam()
const order = reactive(newOrder())
const paying = ref(false)

const plan = computed(() => props.plans.find((p) => p.name === order.plan))
const hasBillingAddress = computed(() =>
	Boolean(team.doc.billing_details?.name),
)
const price = computed(() =>
	money(plan.value.yearly_price, plan.value.currency),
)

const submit = createResource({
	url: 'press.api.enterprise_contract.submit',
	makeParams: () => ({ order }),
	onSuccess: ({ contract, message }) => {
		if (message) toast.info(message)
		emit('placed', contract)
	},
	onError: () => (paying.value = false),
})

function newOrder() {
	const user = team.doc.user_info || {}
	const [firstPlan] = props.plans
	return {
		plan: firstPlan.name,
		billing_email: user.email || '',
		contact_person: `${user.first_name || ''} ${user.last_name || ''}`.trim(),
		designation: '',
		billing_partner: '',
		legal_entities_covered: team.doc.billing_name || '',
		price_lock_years: 1,
	}
}

function selectPlan(selected) {
	order.plan = selected.name
	order.price_lock_years = 1
}

function lockedUntil(years) {
	return dayjs().add(years, 'year').subtract(1, 'day')
}

// Loading stays on until the contract page opens.
function pay() {
	paying.value = true
	submit.submit()
}

// Same selected/unselected styles as the plan cards in NewServer.vue.
function tileClass(selected) {
	return [
		selected
			? 'border-outline-gray-5 ring-1 ring-gray-900 hover:bg-surface-gray-2'
			: 'border-outline-gray-3 bg-surface-white hover:bg-surface-gray-1',
		'flex w-full flex-col rounded-md border text-left',
	]
}
</script>
