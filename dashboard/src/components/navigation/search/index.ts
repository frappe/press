import { h, computed } from 'vue';
import { getTeam } from '@/data/team';
import { session } from '@/data/session';
import { integrations } from './integrations';
import { setTheme } from '@/utils/useTheme';
import { Badge } from 'frappe-ui';

export const index = computed(() => {
	const team = getTeam();

	const groups = {
		'Paramètres': {
			items: [
				{ name: 'Profil', route: '/settings/profile', icon: LucideUser },

				{
					name: "Équipe",
					route: "/settings/team",
					icon: LucideUsers,
					condition:
						team.doc?.user === session.user ||
						session.isTeamAdmin ||
						session.isSystemUser,
				},

				{ name: 'Développeur', route: '/settings/developer', icon: LucideCode },

				{
					name: 'Rôles',
					route: '/settings/permissions/roles',
					icon: LucideLock,
         	condition:
						team.doc?.user === session.user ||
						session.isTeamAdmin ||
						session.isSystemUser,
				},
			],
		},

		'État': {
			items: [
				{
					name: 'Incidents en cours',
					route: '/status/ongoing-incidents',
					icon: LucideTriangleAlert,
				},
				{
					name: 'Historique des incidents',
					route: '/status/incident-history',
					icon: LucideArchive,
				},
			],
		},

		'Outils Dev': {
			condition: team.doc?.onboarding?.complete && !team.doc?.is_saas_user,
			items: [
				{
					name: 'Analyseur de base de données',
					route: '/database-analyzer',
					icon: LucideActivity,
				},
				{
					name: 'SQL Playground',
					route: '/sql-playground',
					icon: LucideDatabaseZap,
				},
				{
					name: 'Navigateur Binlog',
					route: '/binlog-browser',
					icon: LucideFileSearch,
					condition: team.doc?.is_binlog_indexer_enabled ?? false,
				},
			],
		},

		'Facturation': {
			condition: team.doc?.is_desk_user || session.hasBillingAccess,
			items: [
				{ name: 'Aperçu', route: '/billing', icon: LucideWalletCards },
				{
					name: 'Prévisions',
					route: '/billing/forecast',
					icon: LucideTrendingUpDown,
				},
				{
					name: 'Factures',
					route: '/billing/invoices',
					icon: LucideReceiptText,
				},
				{ name: 'Soldes', route: '/billing/balances', icon: LucideWeight },
				{
					name: 'Moyens de paiement',
					route: '/billing/payment-methods',
					icon: LucideCreditCard,
				},
				{
					name: 'Paiements Marketplace',
					route: '/billing/payouts',
					icon: LucideStore,
					condition: team.doc?.is_desk_user,
				},
				{
					name: 'Factures Mpesa',
					route: '/billing/mpesa-invoices',
					icon: LucideReceiptText,
					condition: team.doc?.is_desk_user,
				},
				{
					name: 'Prélèvement auto UPI',
					route: '/billing/upi-autopay',
					icon: LucideWalletCards,
					condition: team.doc?.is_desk_user,
				},
			],
		},

		'Admin Partenaires': {
			condition: team.doc?.is_desk_user,
			items: [
				{
					name: 'Liste des partenaires',
					route: '/settings/partner-admin/partner-list',
					icon: LucideShield,
				},
				{
					name: 'Liste des certificats',
					route: '/settings/partner-admin/certificate-list',
					icon: LucideShield,
				},
				{
					name: 'Prospects admin',
					route: '/settings/partner-admin/partner-admin-lead-list',
					icon: LucideShield,
				},
				{
					name: 'Ressources admin',
					route: '/settings/partner-admin/admin-resources',
					icon: LucideShield,
				},
				{
					name: 'Audits admin',
					route: '/settings/partner-admin/admin-audits',
					icon: LucideShield,
				},
			],
		},

		'Partenariat': {
			condition: Boolean(team.doc?.erpnext_partner),
			items: [
				{ name: 'Aperçu', route: '/partners/overview', icon: LucideGlobe },
				{
					name: 'Détails du site web',
					route: '/partners/website-details',
					icon: LucideGlobe,
				},
				{ name: 'Clients', route: '/partners/customers', icon: LucideGlobe },
				{ name: 'Prospects', route: '/partners/partner-leads', icon: LucideGlobe },
				{
					name: 'Certificats',
					route: '/partners/certificates',
					icon: LucideGlobe,
				},
				{ name: 'Ressources', route: '/partners/resources', icon: LucideGlobe },
				{
					name: 'Contributions',
					route: '/partners/contributions',
					icon: LucideGlobe,
				},
				{ name: 'Audits', route: '/partners/audits', icon: LucideGlobe },
				{
					name: 'Configuration paiement local',
					route: '/partners/local-payment-setup',
					icon: LucideGlobe,
				},
				{
					name: 'Versement',
					route: '/partners/payment-payout',
					icon: LucideGlobe,
				},
				{
					name: 'Tableau de bord',
					route: '/partners/partner-dashboard',
					icon: LucideGlobe,
				},
			],
		},
		Actions: {
			items: [
				{
					name: "Demande d'accès",
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

		'Thème': {
			items: [
				{
					name: 'Mode sombre',
					click: () => setTheme('dark'),
					icon: LucideSun,
					suffix: () => h(Badge, { label: 'beta', class: 'ml-auto' }),
				},
				{
					name: 'Mode clair',
					click: () => setTheme('light'),
					icon: LucideMoon,
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
