<template>
	<div class="flex h-full flex-col">
		<div class="sticky top-0 z-10 shrink-0">
			<Header>
				<FBreadcrumbs
					:items="[{ label: 'Partenariat', route: { name: 'Partnership' } }]"
				/>
			</Header>
		</div>
		<TabsWithRouter
			v-if="
				Boolean(this.$team.doc.erpnext_partner) && $session.hasPartnerAccess
			"
			:tabs="tabs"
		/>
		<div
			v-else
			class="mx-auto mt-60 w-fit rounded border border-dashed px-12 py-8 text-center text-ink-gray-6"
		>
			<lucide-alert-triangle class="mx-auto mb-4 h-6 w-6 text-red-600" />
			<ErrorMessage
				message="Vous n'êtes pas autorisé à voir la page partenaire. Veuillez demander au propriétaire de l'équipe de fournir les permissions pour votre rôle."
			/>
		</div>
	</div>
</template>

<script>
import Header from '../components/Header.vue';
import { Breadcrumbs, Tabs } from 'frappe-ui';
import TabsWithRouter from '../components/TabsWithRouter.vue';

export default {
	name: 'Partner',
	components: {
		Header,
		FBreadcrumbs: Breadcrumbs,
		FTabs: Tabs,
		TabsWithRouter,
	},
	data() {
		return {
			currentTab: 0,
			tabs: [
				{
					label: 'Aperçu',
					route: { name: 'PartnerOverview' },
					condition: () => Boolean(this.$team.doc.erpnext_partner),
				},
				{
					label: 'Détails du site web',
					route: { name: 'PartnerWebsiteDetails' },
					condition: () => Boolean(this.$team.doc.erpnext_partner),
				},
				{
					label: 'Tableau de bord',
					route: { name: 'PartnerDashboard' },
					condition: () =>
						Boolean(
							this.$team.doc.erpnext_partner &&
							this.$team.doc.partner_status === 'Active' &&
							this.$session.hasPartnerDashboardAccess,
						),
				},
				{
					label: 'Clients',
					route: { name: 'PartnerCustomers' },
					condition: () =>
						Boolean(
							this.$team.doc.erpnext_partner &&
							this.$team.doc.partner_status === 'Active' &&
							this.$session.hasPartnerCustomerAccess,
						),
				},
				{
					label: 'Prospects',
					route: { name: 'PartnerLeads' },
					condition: () =>
						Boolean(
							this.$team.doc.erpnext_partner &&
							this.$team.doc.partner_status === 'Active' &&
							this.$session.hasPartnerLeadsAccess,
						),
				},
				{
					label: 'Certifications',

					route: { name: 'PartnerCertificates' },
					condition: () =>
						Boolean(
							this.$team.doc.erpnext_partner &&
							this.$team.doc.partner_status === 'Active',
						),
				},
				{
					label: 'Ressources',
					route: { name: 'PartnerResources' },
					condition: () =>
						Boolean(
							this.$team.doc.erpnext_partner &&
							this.$team.doc.partner_status === 'Active',
						),
				},
				{
					label: 'Contributions',

					route: { name: 'PartnerContributions' },
					condition: () =>
						Boolean(
							this.$team.doc.erpnext_partner &&
							this.$team.doc.partner_status === 'Active' &&
							this.$session.hasPartnerContributionAccess,
						),
				},
				{
					label: 'Audits',
					route: { name: 'PartnerAudits' },
					condition: () =>
						Boolean(
							this.$team.doc.erpnext_partner &&
							this.$team.doc.partner_status === 'Active',
						),
				},
				{
					label: 'Configuration paiement local',
					route: { name: 'LocalPaymentSetup' },
					condition: () =>
						Boolean(
							this.$team.doc.country === 'Kenya' &&
							this.$team.doc.mpesa_enabled &&
							this.$team.doc.erpnext_partner &&
							this.$team.doc.partner_status === 'Active',
						),
				},
				{
					label: 'Versement partenaire',
					route: { name: 'PartnerPayout' },
					condition: () =>
						Boolean(
							this.$team.doc.country === 'Kenya' &&
							this.$team.doc.mpesa_enabled,
						),
				},
			],
		};
	},
};
</script>
