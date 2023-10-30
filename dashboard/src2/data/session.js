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
		onSuccess(data) {
			session.user = getSessionUser();
			session.login.reset();
			router.replace(data.default_route || '/');
		}
	}),
	logout: createResource({
		url: 'logout',
		onSuccess() {
			session.user = getSessionUser();
			router.replace({ name: 'Login' });
		}
	}),
	user: getSessionUser(),
	isLoggedIn: computed(() => !!session.user)
});

export default session;

export function getSessionUser() {
	let cookies = new URLSearchParams(document.cookie.split('; ').join('&'));
	let sessionUser = cookies.get('user_id');
	if (sessionUser === 'Guest') {
		sessionUser = null;
	}
	return sessionUser;
}
