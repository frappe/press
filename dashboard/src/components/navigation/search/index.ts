import { computed } from 'vue';
import { getTeam } from '@/data/team';
import { session } from '@/data/session';
import { integrations } from './integrations';

export const index = computed(() => {
	const team = getTeam();

	const groups = {
		Settings: {
			items: [
				{ name: 'Profile', route: '/settings/profile', icon: LucideUser },
				{ name: 'Team', route: '/settings/team', icon: LucideUsers },
				{ name: 'Developer', route: '/settings/developer', icon: LucideCode },
				{
					name: 'Roles',
					route: '/settings/permissions/roles',
					icon: LucideLock,
				},
			],
		},

		Status: {
			items: [
				{
					name: 'Ongoing Incidents',
					route: '/status/ongoing-incidents',
					icon: LucideTriangleAlert,
				},
				{
					name: 'Incident History',
					route: '/status/incident-history',
					icon: LucideArchive,
				},
			],
		},

		'Dev Tools': {
			condition: team.doc?.onboarding?.complete && !team.doc?.is_saas_user,
			items: [
				{
					name: 'Database Analyzer',
					route: '/database-analyzer',
					icon: LucideActivity,
				},
				{
					name: 'SQL Playground',
					route: '/sql-playground',
					icon: LucideDatabaseZap,
				},
				{
					name: 'Binlog Browser',
					route: '/binlog-browser',
					icon: LucideFileSearch,
					condition: team.doc?.is_binlog_indexer_enabled ?? false,
				},
			],
		},

		Billing: {
			condition: team.doc?.is_desk_user || session.hasBillingAccess,
			items: [
				{ name: 'Overview', route: '/billing', icon: LucideWalletCards },
				{
					name: 'Forecast',
					route: '/billing/forecast',
					icon: LucideTrendingUpDown,
				},
				{
					name: 'Invoices',
					route: '/billing/invoices',
					icon: LucideReceiptText,
				},
				{ name: 'Balances', route: '/billing/balances', icon: LucideWeight },
				{
					name: 'Payment Methods',
					route: '/billing/payment-methods',
					icon: LucideCreditCard,
				},
				{
					name: 'Marketplace Payouts',
					route: '/billing/payouts',
					icon: LucideStore,
					condition: team.doc?.is_desk_user,
				},
				{
					name: 'Mpesa Invoices',
					route: '/billing/mpesa-invoices',
					icon: LucideReceiptText,
					condition: team.doc?.is_desk_user,
				},
				{
					name: 'UPI Autopay',
					route: '/billing/upi-autopay',
					icon: LucideWalletCards,
					condition: team.doc?.is_desk_user,
				},
			],
		},

		'Partner Admin': {
			condition: team.doc?.is_desk_user,
			items: [
				{
					name: 'Partner List',
					route: '/settings/partner-admin/partner-list',
					icon: LucideShield,
				},
				{
					name: 'Certificate List',
					route: '/settings/partner-admin/certificate-list',
					icon: LucideShield,
				},
				{
					name: 'Admin Leads',
					route: '/settings/partner-admin/partner-admin-lead-list',
					icon: LucideShield,
				},
				{
					name: 'Admin Resources',
					route: '/settings/partner-admin/admin-resources',
					icon: LucideShield,
				},
				{
					name: 'Admin Audits',
					route: '/settings/partner-admin/admin-audits',
					icon: LucideShield,
				},
			],
		},

		Partnership: {
			condition: Boolean(team.doc?.erpnext_partner),
			items: [
				{ name: 'Overview', route: '/partners/overview', icon: LucideGlobe },
				{
					name: 'Website Details',
					route: '/partners/website-details',
					icon: LucideGlobe,
				},
				{ name: 'Customers', route: '/partners/customers', icon: LucideGlobe },
				{ name: 'Leads', route: '/partners/partner-leads', icon: LucideGlobe },
				{
					name: 'Certificates',
					route: '/partners/certificates',
					icon: LucideGlobe,
				},
				{ name: 'Resources', route: '/partners/resources', icon: LucideGlobe },
				{
					name: 'Contributions',
					route: '/partners/contributions',
					icon: LucideGlobe,
				},
				{ name: 'Audits', route: '/partners/audits', icon: LucideGlobe },
				{
					name: 'Local Payment Setup',
					route: '/partners/local-payment-setup',
					icon: LucideGlobe,
				},
				{
					name: 'Payout',
					route: '/partners/payment-payout',
					icon: LucideGlobe,
				},
				{
					name: 'Dashboard',
					route: '/partners/partner-dashboard',
					icon: LucideGlobe,
				},
			],
		},
		Actions: {
			items: [
				{
					name: 'Access Request',
					icon: LucideKey,
					click: () => {
						document
							.querySelector('button[aria-label="Notifications btn"]')
							.click();
						setTimeout(() => {
							const tab = document.querySelectorAll(
								'.PopoverContent [role="tab"]',
							)[1];
							tab.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
						}, 0);
					},
				},
			],
		},
	};

	for (const [key, value] of Object.entries(integrations)) {
		groups[key] = {
			...value,
			items: value.items.filter((item) => item.condition ?? true),
		};
	}

	return Object.fromEntries(
		Object.entries(groups)
			.filter(([_, section]) => section.condition ?? true)
			.map(([name, section]) => [
				name,
				{
					...section,
					items: section.items.filter((item) => item.condition ?? true),
				},
			]),
	);
});
