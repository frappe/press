<template>
	<div class="flex h-full flex-col">
		<div class="sticky top-0 z-10 shrink-0">
			<Header>
				<FBreadcrumbs
					:items="[{ label: 'Partnership', route: { name: 'Partnership' } }]"
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
			class="mx-auto mt-60 w-fit rounded border border-dashed px-12 py-8 text-center text-gray-600"
		>
			<lucide-alert-triangle class="mx-auto mb-4 h-6 w-6 text-red-600" />
			<ErrorMessage
				message="You aren't permitted to view the partner page. Please ask the team owner to provide permission for your role."
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
					label: 'Overview',
					route: { name: 'PartnerOverview' },
					condition: () => Boolean(this.$team.doc.erpnext_partner),
				},
				{
					label: 'Website Details',
					route: { name: 'PartnerWebsiteDetails' },
					condition: () => Boolean(this.$team.doc.erpnext_partner),
				},
				{
					label: 'Dashboard',
					route: { name: 'PartnerDashboard' },
					condition: () =>
						Boolean(
							this.$team.doc.erpnext_partner &&
								this.$team.doc.partner_status === 'Active' &&
								this.$session.hasPartnerDashboardAccess,
						),
				},
				{
					label: 'Customers',
					route: { name: 'PartnerCustomers' },
					condition: () =>
						Boolean(
							this.$team.doc.erpnext_partner &&
								this.$team.doc.partner_status === 'Active' &&
								this.$session.hasPartnerCustomerAccess,
						),
				},
				{
					label: 'Leads',
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
					label: 'Resources',
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
					label: 'Local Payment Setup',
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
					label: 'Partner Payout',
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
