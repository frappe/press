import call from './call';
import Auth from './auth';
import socket from './socket';
import Account from './account';
import Saas from './saas';

import { reactive } from 'vue';

const auth = reactive(new Auth());
const account = reactive(new Account());
const saas = reactive(new Saas());

export default function registerControllers(app) {
	// Hack to get $auth working, should be refactored later
	app.config.globalProperties.$call = call;
	app.config.globalProperties.$socket = socket;
	app.config.globalProperties.$auth = auth;
	app.config.globalProperties.$account = account;
	app.config.globalProperties.$saas = saas;

	// Actually, provide-inject is recommended to be used
	app.provide('$auth', auth);
	app.provide('$account', account);
	app.provide('$call', call);
	app.provide('$socket', socket);
	app.provide('$saas', saas);

	// global accessor to expose switchToTeam method
	window.$account = account;
	window.$saas = saas;

	return {
		auth,
		account,
		call,
		socket,
		saas
	};
}
