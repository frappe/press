import { computed, reactive } from 'vue';
import { createResource } from 'frappe-ui';
import { clear } from 'idb-keyval';
import router from '../router';

export let session = reactive({
	login: createResource({
		url: 'login',
		makeParams({ email, password }) {
			return {
				usr: email,
				pwd: password,
			};
		},
	}),
	logout: createResource({
		url: 'logout',
		async onSuccess() {
			session.user = getSessionUser();
			await router.replace({ name: 'Login' });
			localStorage.removeItem('current_team');
			// On logout, reset posthog user identity and device id
			if (window.posthog?.__loaded) {
				posthog.reset(true);
			}

			// clear all cache from the session
			clear();

			window.location.reload();
		},
	}),
	logoutWithoutReload: createResource({
		url: 'logout',
		async onSuccess() {
			session.user = getSessionUser();
			localStorage.removeItem('current_team');
			// On logout, reset posthog user identity and device id
			if (window.posthog?.__loaded) {
				posthog.reset(true);
			}

			clear();
		},
	}),
	userPermissions: createResource({
		url: 'press.api.account.user_permissions',
		cache: [
			'userPermissions',
			localStorage.getItem('current_team'),
			getSessionUser(),
		],
		initialData: {
			owner: false,
			admin: false,
			billing: false,
			webhook: false,
			apps: false,
			partner: false,
			partner_dashboard: false,
			partner_leads: false,
			partner_customer: false,
			partner_contribution: false,
			site_creation: false,
			bench_creation: false,
			server_creation: false,
		},
	}),
	isTeamAdmin: computed(() => session.userPermissions.data.admin),
	hasBillingAccess: computed(() => session.userPermissions.data.billing),
	hasWebhookConfigurationAccess: computed(
		() => session.userPermissions.data.webhook,
	),
	hasAppsAccess: computed(() => session.userPermissions.data.apps),
	hasPartnerAccess: computed(() => session.userPermissions.data.partner),
	hasPartnerDashboardAccess: computed(
		() => session.userPermissions.data.partner_dashboard,
	),
	hasPartnerLeadsAccess: computed(
		() => session.userPermissions.data.partner_leads,
	),
	hasPartnerCustomerAccess: computed(
		() => session.userPermissions.data.partner_customer,
	),
	hasPartnerContributionAccess: computed(
		() => session.userPermissions.data.partner_contribution,
	),
	hasSiteCreationAccess: computed(
		() => session.userPermissions.data.site_creation,
	),
	hasBenchCreationAccess: computed(
		() => session.userPermissions.data.bench_creation,
	),
	hasServerCreationAccess: computed(
		() => session.userPermissions.data.server_creation,
	),
	user: getSessionUser(),
	userFullName: getSessionCookies().get('full_name') || '',
	isLoggedIn: computed(() => !!session.user),
	isSystemUser: getSessionCookies().get('system_user') === 'yes',
});

export default session;

export function getSessionUser() {
	let cookies = getSessionCookies();
	let sessionUser = cookies.get('user_id');
	if (!sessionUser || sessionUser === 'Guest') {
		sessionUser = null;
	}
	return sessionUser;
}

function getSessionCookies() {
	return new URLSearchParams(document.cookie.split('; ').join('&'));
}
