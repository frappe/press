<template>
	<div class="sticky top-0 z-10 shrink-0">
		<Header>
			<FBreadcrumbs
				:items="[{ label: 'Facturation', route: { name: 'Billing' } }]"
			/>
		</Header>
		<TabsWithRouter
			v-if="$team?.doc?.is_desk_user || $session.hasBillingAccess"
			:tabs="tabs"
		/>
		<div
			v-else
			class="mx-auto mt-60 w-fit rounded border border-dashed px-12 py-8 text-center text-ink-gray-6"
		>
			<lucide-alert-triangle class="mx-auto mb-4 h-6 w-6 text-red-600" />
			<ErrorMessage message="Vous n'êtes pas autorisé à voir la page de facturation" />
		</div>
	</div>
</template>
<script>
import { Breadcrumbs, Tabs } from 'frappe-ui'
import Header from '../components/Header.vue'
import TabsWithRouter from '../components/TabsWithRouter.vue'

export default {
	name: 'Billing',
	components: {
		Header,
		FBreadcrumbs: Breadcrumbs,
		FTabs: Tabs,
		TabsWithRouter,
	},
	data() {
		return {
			currentTab: 0,
		}
	},
	computed: {
		tabs() {
			const baseTabs = [
				{ label: 'Aperçu', route: { name: 'BillingOverview' } },
				{ label: 'Prévisions', route: { name: 'BillingForecast' } },
				{ label: 'Factures', route: { name: 'BillingInvoices' } },
				{ label: 'Soldes', route: { name: 'BillingBalances' } },
				{ label: 'Modes de paiement', route: { name: 'BillingPaymentMethods' } },
				{
					label: 'Paiements Marketplace',
					route: { name: 'BillingMarketplacePayouts' },
				},
			]

			if (this.$team?.doc?.apply_limits && this.$team?.doc?.tier) {
				baseTabs.push({ label: 'Niveaux', route: { name: 'BillingTiers' } })
			}

			// Add UPI Autopay tab pour les équipes DZD
			if (this.$team?.doc?.currency === 'DZD') {
				baseTabs.splice(5, 0, {
					label: 'Prélèvement automatique',
					route: { name: 'BillingUPIAutopay' },
				})
			}

			return baseTabs
		},
	},
}
</script>
