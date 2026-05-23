<template>
	<div class="flex flex-1 flex-col gap-6 overflow-y-auto px-20 pb-12 pt-6">
		<div class="flex flex-col gap-1">
			<h2 class="text-xl font-semibold text-ink-gray-9">Niveaux d'équipe</h2>
			<p class="max-w-3xl text-p-base text-ink-gray-6">
				Les niveaux d'équipe déterminent votre limite de dépenses mensuelles sur Frappe Cloud. Vous
				êtes automatiquement déplacé vers un niveau supérieur une fois que votre utilisation et votre
				historique de paiement remplissent les conditions ci-dessous.
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
			<!-- Your current standing -->
			<div
				class="rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-4"
			>
				<div class="flex flex-wrap items-center justify-between gap-3">
					<div class="flex flex-col gap-1">
						<div class="text-sm font-medium text-ink-gray-6">
							Votre niveau actuel
						</div>
						<div class="flex items-center gap-2">
							<span class="text-lg font-semibold text-ink-gray-9">
								{{ currentTierLabel }}
							</span>
							<Badge
								v-if="teamTiers.data.current_tier"
								theme="blue"
								:label="`Limite de dépenses ${formatAmount(teamTiers.data.spending_limit)}`"
							/>
						</div>
					</div>
					<div class="flex flex-col gap-1 text-right">
						<div class="text-sm text-ink-gray-6">
							Client payant depuis
							<span class="font-medium text-ink-gray-9">
								{{ payingSinceLabel }}
							</span>
						</div>
						<div class="text-sm text-ink-gray-6">
							Dernière facture payée
							<span class="font-medium text-ink-gray-9">
								{{ formatAmount(metrics.last_invoice_amount, skip_format=1) }}
							</span>
						</div>
					</div>
				</div>
			</div>

			<!-- Tier cards -->
			<div class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
				<div
					v-for="(tier, idx) in teamTiers.data.tiers"
					:key="tier.name"
					class="flex flex-col gap-4 rounded-lg border bg-surface-white p-5 shadow-sm transition-all"
					:class="
						isCurrentTier(tier)
							? 'border-outline-blue-2 ring-1 ring-outline-blue-2'
							: 'border-outline-gray-2'
					"
				>
					<div class="flex items-start justify-between">
						<div class="flex flex-col gap-1">
							<div
								class="text-sm font-medium uppercase tracking-wide text-ink-gray-5"
							>
								Niveau {{ idx }}
							</div>
							<div class="text-lg font-semibold text-ink-gray-9">
								{{ tier.tier }}
							</div>
						</div>
						<Badge v-if="isCurrentTier(tier)" theme="blue" label="Actuel" />
						<Badge
							v-else-if="qualifiesForTier(tier)"
							theme="green"
							label="Éligible"
						/>
					</div>

					<div class="flex items-baseline gap-1">
						<span class="text-3xl font-semibold text-ink-gray-9">
							{{ formatAmount(tier.amount) }}
						</span>
						<span class="text-sm text-ink-gray-6">limite de dépenses</span>
					</div>

					<div class="border-t border-outline-gray-1" />

					<div class="flex flex-col gap-2">
						<div
							class="text-xs font-medium uppercase tracking-wide text-ink-gray-5"
						>
							Comment se qualifier
						</div>
						<ul class="flex flex-col gap-2 text-sm text-ink-gray-7">
							<li v-for="(req, i) in requirementsFor(tier, idx)" :key="i">
								<div class="flex items-center gap-2">
									<lucide-check-circle-2
										v-if="req.met"
										class="h-4 w-4 shrink-0 text-ink-green-3"
									/>
									<lucide-circle
										v-else
										class="h-4 w-4 shrink-0 text-ink-gray-4"
									/>
									<span :class="req.met ? 'text-ink-gray-9' : ''">
										{{ req.text }}
									</span>
								</div>
							</li>
						</ul>
					</div>
				</div>
			</div>

			<!-- How tiers work -->
			<div class="rounded-lg border border-outline-gray-2 bg-surface-white p-5">
				<div class="flex items-start gap-3">
					<lucide-info class="mt-0.5 h-5 w-5 shrink-0 text-ink-gray-5" />
					<div class="flex flex-col gap-2">
						<div class="text-base font-medium text-ink-gray-9">
							Comment fonctionnent les niveaux
						</div>
						<ul
							class="flex list-disc flex-col gap-1.5 pl-5 text-sm text-ink-gray-7"
						>
							<li>
								Les niveaux contrôlent le montant maximum que votre équipe peut dépenser
								dans un cycle de facturation.
							</li>
							<li>
								Vous êtes automatiquement promu à un niveau supérieur lorsque votre dernière
								facture d'abonnement payée atteint le seuil de ce niveau et que vous
								avez au moins trois factures consécutives payées.
							</li>
							<li>
								Les nouvelles équipes commencent au niveau de base avec une limite de dépenses par défaut.
								L'ajout d'un mode de paiement ou l'achat de crédits prépayés est requis pour
								rester au niveau de base ou au-dessus.
							</li>
							<li>
								Besoin d'une limite plus élevée immédiatement ? Contactez le support et nous
								examinerons votre compte.
							</li>
						</ul>
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
	const isDZD = team.doc.currency === 'DZD'
	const symbol = isDZD ? 'DA' : '$'
	let amount = isDZD ? Number(value) * 135 : Number(value)
	if (skip_format) {
		amount = Number(value)
	}
	return `${symbol}${amount.toLocaleString('en-US', {
		maximumFractionDigits: 2,
	})}`
}

const currentTierLabel = computed(() => {
	const current = teamTiers.data?.current_tier
	if (!current) return 'Non défini'
	return current
})

const payingSinceLabel = computed(() => {
	const months = metrics.value.paying_since_months ?? 0
	if (!months) return '—'
	if (months === 1) return '1 mois'
	return `${months} mois`
})

function isCurrentTier(tier) {
	return teamTiers.data?.current_tier === tier.name
}

function tierInvoiceThresholdInTeamCurrency(tier) {
	// tier.last_invoice_amount is stored in USD; metrics.last_invoice_amount is in team currency.
	// Convert the tier threshold to the team's currency before comparing.
	const isDZD = team.doc.currency === 'DZD'
	return isDZD
		? Number(tier.last_invoice_amount ?? 0) * 135
		: Number(tier.last_invoice_amount ?? 0)
}

function qualifiesForTier(tier) {
	const m = metrics.value
	// Base tier: needs a payment method or prepaid credits
	if (!tier.paying_user_since && !tier.last_invoice_amount) {
		return !!m.has_payment_method
	}
	const monthsOk = (m.paying_since_months ?? 0) >= (tier.paying_user_since ?? 0)
	const invoiceOk =
		(m.last_invoice_amount ?? 0) >= tierInvoiceThresholdInTeamCurrency(tier)
	return monthsOk && invoiceOk
}

function requirementsFor(tier, idx) {
	const m = metrics.value
	// Base tier (no historical conditions): payment method / prepaid credits
	if (!tier.paying_user_since && !tier.last_invoice_amount) {
		return [
			{
				text: 'Mode de paiement ajouté ou crédits prépayés disponibles',
				met: !!m.has_payment_method,
			},
		]
	}
	return [
		{
			text: `Utilisateur payant depuis au moins ${tier.paying_user_since} mois`,
			met: (m.paying_since_months ?? 0) >= (tier.paying_user_since ?? 0),
		},
		{
			text: `Dernière facture payée ≥ ${formatAmount(tier.last_invoice_amount)}`,
			met:
				(m.last_invoice_amount ?? 0) >=
				tierInvoiceThresholdInTeamCurrency(tier),
		},
	]
}
</script>
