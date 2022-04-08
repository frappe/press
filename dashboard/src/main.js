import App from './App.vue';
import utils from './utils';
import router from './router';
import call from './controllers/call';
import Auth from './controllers/auth';
import socket from './controllers/socket';
import Account from './controllers/account';
import resourceManager from './resourceManager';
import registerGlobalComponents from './components/global/register';

import { createApp, reactive } from 'vue';

const app = createApp(App);
const auth = reactive(new Auth());
const account = reactive(new Account());

registerGlobalComponents(app);

app.use(resourceManager);
app.use(utils);
app.use(router);

app.config.globalProperties.$call = call;
app.provide('$call', call);

// Hack to get $auth working, should be refactored later
app.config.globalProperties.$auth = auth;
// Actually, provide-inject is recommended to be used
app.provide('$auth', auth);

app.config.globalProperties.$socket = socket;
app.provide('$account', account);
app.config.globalProperties.$account = account;
app.provide('$socket', socket);

// global accessor to expose switchToTeam method
window.$account = account;

app.mount('#app');

app.config.errorHandler = (error, instance) => {
	if (instance) {
		instance.$notify({
			icon: 'x',
			title: 'An error occurred',
			message: error.messages?.join('\n'),
			color: 'red'
		});
	}
	console.error(error);
};

router.beforeEach(async (to, from, next) => {
	if (to.name == 'Home') {
		next({ name: 'Welcome' });
		return;
	}

	if (to.matched.some(record => !record.meta.isLoginPage)) {
		// this route requires auth, check if logged in
		// if not, redirect to login page.
		if (!auth.isLoggedIn) {
			next({ name: 'Login', query: { route: to.path } });
		} else {
			if (!account.user) {
				await account.fetchAccount();
			}
			next();
		}
	} else {
		// if already logged in, route to /welcome
		if (auth.isLoggedIn) {
			if (!account.user) {
				await account.fetchAccount();
			}
			next({ name: 'Welcome' });
		} else {
			next();
		}
	}
});
