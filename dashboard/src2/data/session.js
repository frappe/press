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
				pwd: password
			};
		}
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
		}
	}),
	roles: createResource({
		url: 'press.api.account.get_permission_roles',
		cache: ['roles', localStorage.getItem('current_team')],
		initialData: []
	}),
	isTeamAdmin: computed(
		() =>
			session.roles.data.length
				? session.roles.data.some(role => role.admin_access)
				: false // if no roles, assume not admin and has member access
	),
	hasBillingAccess: computed(() =>
		session.roles.data.length
			? session.roles.data.some(role => role.allow_billing)
			: true
	),
	hasWebhookConfigurationAccess: computed(() =>
		session.roles.data.length
			? session.roles.data.some(role => role.allow_webhook_configuration)
			: true
	),
	hasAppsAccess: computed(() =>
		session.roles.data.length
			? session.roles.data.some(role => role.allow_apps)
			: true
	),
	hasPartnerAccess: computed(() =>
		session.roles.data.length
			? session.roles.data.some(role => role.allow_partner)
			: true
	),
	hasSiteCreationAccess: computed(() =>
		session.roles.data.length
			? session.roles.data.some(role => role.allow_site_creation)
			: true
	),
	hasBenchCreationAccess: computed(() =>
		session.roles.data.length
			? session.roles.data.some(role => role.allow_bench_creation)
			: true
	),
	hasServerCreationAccess: computed(() =>
		session.roles.data.length
			? session.roles.data.some(role => role.allow_server_creation)
			: true
	),
	user: getSessionUser(),
	isLoggedIn: computed(() => !!session.user),
	isSystemUser: getSessionCookies().get('system_user') === 'yes'
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
