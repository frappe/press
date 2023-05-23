import call from './call';
import Auth from './auth';
import socket from './socket';
import Account from './account';

import { reactive } from 'vue';

const auth = reactive(new Auth());
const account = reactive(new Account());

export default function registerControllers(app) {
	// Hack to get $auth working, should be refactored later
	app.config.globalProperties.$call = call;
	app.config.globalProperties.$socket = socket;
	app.config.globalProperties.$auth = auth;
	app.config.globalProperties.$account = account;

	// Actually, provide-inject is recommended to be used
	app.provide('$auth', auth);
	app.provide('$account', account);
	app.provide('$call', call);
	app.provide('$socket', socket);

	// global accessor to expose switchToTeam method
	window.$account = account;

	return {
		auth,
		account,
		call,
		socket
	};
}
