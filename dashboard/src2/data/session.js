import { computed, reactive } from 'vue';
import { createResource } from 'frappe-ui';
import router from '../router';

let session = reactive({
	login: createResource({
		url: 'login',
		makeParams({ email, password }) {
			return {
				usr: email,
				pwd: password
			};
		},
		onSuccess() {
			window.location.reload();
		}
	}),
	logout: createResource({
		url: 'logout',
		async onSuccess() {
			session.user = getSessionUser();
			await router.replace({ name: 'Login' });
			window.location.reload();
		}
	}),
	user: getSessionUser(),
	isLoggedIn: computed(() => !!session.user)
});

export default session;

export function getSessionUser() {
	let cookies = new URLSearchParams(document.cookie.split('; ').join('&'));
	let sessionUser = cookies.get('user_id');
	if (!sessionUser || sessionUser === 'Guest') {
		sessionUser = null;
	}
	return sessionUser;
}
