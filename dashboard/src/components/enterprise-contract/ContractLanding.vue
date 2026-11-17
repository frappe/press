<template>
	<div class="mx-auto flex max-w-4xl flex-col gap-5 py-6">
		<template v-if="premiumServers.length">
			<div
				class="flex gap-3 rounded-md border border-green-200 bg-green-50 p-5"
			>
				<lucide-shield-check class="size-5 shrink-0 text-green-700" />
				<div class="flex flex-col gap-1">
					<h2 class="text-lg font-medium text-green-900">
						Enterprise support is included with your premium
						{{ premiumServers.length === 1 ? "server" : "servers" }}
					</h2>
					<p class="text-base text-green-800">
						Sites on these servers are already covered. You do not need a
						warranty contract for them.
					</p>
				</div>
			</div>
			<div class="overflow-hidden rounded-md border">
				<div
					class="border-b bg-surface-gray-1 px-5 py-2.5 text-sm text-ink-gray-6"
				>
					Covered servers
				</div>
				<router-link
					v-for="server in premiumServers"
					:key="server.name"
					:to="{ name: 'Server Detail', params: { name: server.name } }"
					class="flex justify-between border-b px-5 py-3 text-base text-ink-gray-8 last:border-b-0 hover:bg-surface-gray-1"
				>
					{{ server.title || server.name }}
					<span class="text-ink-gray-6">Premium</span>
				</router-link>
			</div>
			<h2 class="pt-3 text-lg font-medium text-ink-gray-9">
				Also running Frappe on your own servers?
			</h2>
		</template>

		<div
			v-for="plan in plans"
			:key="plan.name"
			class="flex flex-col gap-6 rounded-md border p-6 md:flex-row"
		>
			<div class="flex flex-1 flex-col gap-2">
				<div
					class="text-sm font-medium uppercase tracking-wide text-ink-gray-6"
				>
					OEM support from Frappe
				</div>
				<h2 class="text-2xl font-semibold text-ink-gray-9">{{ plan.title }}</h2>
				<p class="text-base leading-relaxed text-ink-gray-7">
					{{ plan.description ||
						"A yearly contract with Frappe for the apps you run, on Frappe Cloud or on your own servers." }}
				</p>
				<ul class="mt-2 flex flex-col gap-2 text-base text-ink-gray-8">
					<li v-for="point in points(plan)" :key="point" class="flex gap-2">
						<lucide-check class="mt-0.5 size-4 shrink-0 text-green-600" />
						{{ point }}
					</li>
				</ul>
			</div>
			<div
				class="flex flex-col justify-center gap-3 border-t pt-6 md:w-64 md:border-l md:border-t-0 md:pl-6 md:pt-0"
			>
				<div class="flex items-baseline gap-1.5">
					<span class="text-3xl font-semibold text-ink-gray-9">
						{{ money(plan.yearly_price, plan.currency) }}
					</span>
					<span class="text-base text-ink-gray-6">/ year</span>
				</div>
				<div class="text-sm text-ink-gray-6">Excluding taxes</div>
				<div v-if="orderBlocked" class="text-base text-ink-gray-7">
					{{ orderBlocked }}
				</div>
				<Button
					v-else
					variant="solid"
					size="md"
					label="Order Contract"
					@click="emit('order')"
				/>
			</div>
		</div>

		<div class="flex flex-col gap-3">
			<h3 class="text-base font-medium text-ink-gray-9">How it works</h3>
			<ol class="grid grid-cols-1 gap-3 md:grid-cols-3">
				<li
					v-for="(step, i) in STEPS"
					:key="step.title"
					class="flex flex-col gap-1.5 rounded-md border p-4"
				>
					<span class="text-sm text-ink-gray-6">Step {{ i + 1 }}</span>
					<span class="text-base font-medium text-ink-gray-9">
						{{ step.title }}
					</span>
					<span class="text-base leading-relaxed text-ink-gray-7">
						{{ step.text }}
					</span>
				</li>
			</ol>
		</div>
	</div>
</template>

<script setup>
import { Button } from 'frappe-ui'
import { money } from './format'

defineProps({
	plans: { type: Array, required: true },
	premiumServers: { type: Array, default: () => [] },
	orderBlocked: { type: String, default: null },
})
const emit = defineEmits(['order'])

const STEPS = [
	{
		title: 'Order and pay',
		text: 'Name your legal entities and contact. The year starts on the day you pay.',
	},
	{
		title: 'Frappe signs',
		text: 'We sign the agreement. Then you can download the signed copy from the contract page.',
	},
	{
		title: 'Renew yearly',
		text: 'Renewal opens before the year ends. We never charge you automatically.',
	},
]

// The plan's coverage lines first, as staff wrote them, then what every contract gives.
function points(plan) {
	return [
		...plan.coverage,
		'All the legal entities you name on the contract',
		'Signed agreement from Frappe, downloadable from the contract page',
		'The same price on renewal during the price lock period',
	]
}
</script>
