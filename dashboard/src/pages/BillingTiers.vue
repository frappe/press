<template>
	<div
		class="flex flex-1 flex-col gap-6 overflow-y-auto px-20 pb-12 pt-6 lg:px-60 xl:px-96"
	>
		<div class="flex flex-col gap-1">
			<h2 class="text-3xl-semibold text-ink-gray-9">Spending Limits</h2>
			<p class="text-p-base text-ink-gray-5">
				These determine your monthly spending limit on Frappe Cloud. You are
				automatically moved to a higher tier once your usage and payment history
				meet the qualifying conditions.
			</p>
		</div>

		<!-- Loading -->
		<div
			v-if="teamTiers.loading && !teamTiers.data"
			class="flex h-60 items-center justify-center"
		>
			<Spinner class="h-6" />
		</div>

		<!-- Error -->
		<ErrorMessage v-else-if="teamTiers.error" :message="teamTiers.error" />

		<template v-else-if="teamTiers.data">
			<!-- Current standing -->
			<div
				class="rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-4"
			>
				<div class="flex flex-wrap items-center justify-between gap-3">
					<div class="flex flex-col gap-1">
						<div class="text-sm text-ink-gray-6">Current subscribed amount</div>
						<div class="flex items-center gap-2">
							<span class="text-3xl-semibold text-ink-gray-9">
								{{ formatAmount($team.doc.total_subscribed_amount) }}
							</span>
						</div>
					</div>
					<div class="flex flex-col gap-1 text-right">
						<div class="text-sm text-ink-gray-6">
							Paying since
							<span class="font-medium text-ink-gray-9"
								>{{ payingSinceLabel }}</span
							>
						</div>
						<div class="text-sm text-ink-gray-6">
							Last paid invoice
							<span class="font-medium text-ink-gray-9">
								{{ formatAmount(metrics.last_invoice_amount, 1) }}
							</span>
						</div>
					</div>
				</div>
			</div>

			<!-- Tiers table -->
			<div
				class="overflow-hidden rounded-lg border border-outline-gray-2 bg-surface-base"
			>
				<table class="w-full text-left">
					<thead>
						<tr class="border-b border-outline-gray-2 bg-surface-gray-1">
							<th
								class="px-4 py-3 text-normal font-medium tracking-wide text-ink-gray-5"
							>
								Tier
							</th>
							<th
								class="px-4 py-3 text-normal font-medium tracking-wide text-ink-gray-5"
							>
								Requirements
							</th>
							<th
								class="px-4 py-3 text-right text-normal font-medium tracking-wide text-ink-gray-5"
							>
								Spending Limit
							</th>
						</tr>
					</thead>
					<tbody class="divide-y divide-outline-gray-2">
						<tr
							v-for="(tier, idx) in teamTiers.data.tiers"
							:key="tier.name"
							class="transition-colors hover:bg-surface-gray-1"
						>
							<td class="px-4 py-4 align-middle">
								<div class="flex flex-wrap items-center gap-2">
									<span class="text-sm-semibold text-ink-gray-9">
										{{ tier.tier }}
									</span>
									<Badge
										v-if="isCurrentTier(tier)"
										theme="blue"
										label="Current"
									/>
								</div>
							</td>
							<td class="px-4 py-4 align-top">
								<ul class="flex flex-col gap-1.5">
									<li
										v-for="(req, i) in requirementsFor(tier, idx)"
										:key="i"
										class="flex items-center gap-2"
									>
										<lucide-check-circle-2
											v-if="req.met"
											class="h-3.5 w-3.5 shrink-0 text-ink-green-6"
										/>
										<lucide-circle
											v-else
											class="h-3.5 w-3.5 shrink-0 text-ink-gray-4"
										/>
										<span
											class="text-sm"
											:class="req.met ? 'text-ink-gray-9' : 'text-ink-gray-6'"
										>
											{{ req.text }}
										</span>
									</li>
								</ul>
							</td>
							<td class="px-4 py-4 text-right align-middle">
								<span class="text-sm-semibold text-ink-gray-9">
									{{ formatAmount(tier.amount) }}
								</span>
							</td>
						</tr>
					</tbody>
				</table>
			</div>

			<!-- How tiers work -->
			<div class="rounded-lg border border-outline-gray-2 bg-surface-base p-5">
				<div class="flex items-start">
					<div class="flex flex-col gap-2">
						<div class="flex items-center gap-2">
							<lucide-info class="h-5 w-5 shrink-0 text-ink-gray-5" />
							<div class="text-base-medium text-ink-gray-9">
								How tier upgrades work
							</div>
						</div>
						<div class="flex flex-col gap-2">
							<ul
								class="flex list-disc flex-col gap-1.5 pl-5 text-sm text-ink-gray-7"
							>
								<li>
									Tiers control the maximum amount your team can spend in a
									billing cycle.
								</li>
								<li>
									You are automatically upgraded to a higher tier when your last
									paid subscription invoice meets that tier's threshold and you
									have at least three consecutive paid invoices.
								</li>
								<li>
									New teams start at the base tier with a default spending
									limit. Adding a payment method or buying prepaid credits is
									required to remain at or above the base tier.
								</li>
								<li>
									Need a higher limit immediately? Reach out to
									<a
										href="https://support.frappe.io"
										target="_blank"
										rel="noopener noreferrer"
										class="text-ink-blue-6 underline underline-offset-2 hover:text-ink-blue-8"
									>
										support
									</a>
									and we will review your account.
								</li>
							</ul>
						</div>
					</div>
				</div>
			</div>
		</template>
	</div>
</template>

<script setup>
import { Badge, createResource, ErrorMessage, Spinner } from 'frappe-ui'
import { computed, inject } from 'vue'

const team = inject('team')

const teamTiers = createResource({
	url: 'press.api.billing.team_tiers',
	cache: 'teamTiers',
	auto: true,
})

const metrics = computed(() => teamTiers.data?.team_metrics ?? {})

function formatAmount(value, skip_format = false) {
	if (value == null) return '—'
	const isINR = team.doc.currency === 'INR'
	const symbol = isINR ? '₹' : '$'
	let amount = isINR ? Number(value) * 82 : Number(value)
	if (skip_format) {
		amount = Number(value)
	}
	const value_format = isINR ? 'en-IN' : 'en-US'
	return `${symbol}${amount.toLocaleString(value_format, {
		maximumFractionDigits: 2,
	})}`
}

const payingSinceLabel = computed(() => {
	const months = metrics.value.paying_since_months ?? 0
	if (!months) return '—'
	if (months === 1) return '1 month'
	return `${months} months`
})

function isCurrentTier(tier) {
	return teamTiers.data?.current_tier === tier.name
}

function tierInvoiceThresholdInTeamCurrency(tier) {
	const isINR = team.doc.currency === 'INR'
	return isINR
		? Number(tier.last_invoice_amount ?? 0) * 82
		: Number(tier.last_invoice_amount ?? 0)
}

function requirementsFor(tier, idx) {
	const m = metrics.value
	if (!tier.paying_user_since && !tier.last_invoice_amount) {
		return [
			{
				text: 'Payment method added or prepaid credits available',
				met: !!m.has_payment_method,
			},
		]
	}
	return [
		{
			text: `Paying user for at least ${tier.paying_user_since} months`,
			met: (m.paying_since_months ?? 0) >= (tier.paying_user_since ?? 0),
		},
		{
			text: `Last paid invoice ≥ ${formatAmount(tier.last_invoice_amount)}`,
			met:
				(m.last_invoice_amount ?? 0) >=
				tierInvoiceThresholdInTeamCurrency(tier),
		},
	]
}
</script>
