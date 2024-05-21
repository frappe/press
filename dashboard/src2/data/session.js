import { computed, reactive } from 'vue';
import { createResource } from 'frappe-ui';
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
			window.location.reload();
		}
	}),
	roles: createResource({
		url: 'press.api.account.get_permission_roles',
		cache: ['roles', localStorage.getItem('current_team')],
		initialData: []
	}),
	hasBillingAccess: computed(() =>
		session.roles.data.length
			? session.roles.data.some(role => role.allow_billing)
			: true
	),
	hasAppsAccess: computed(() =>
		session.roles.data.length
			? session.roles.data.some(role => role.allow_apps)
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
