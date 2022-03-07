import { inject } from 'vue';
import App from './App.vue';
import { createApp, reactive } from 'vue';
import outsideClickDirective from '@/components/global/outsideClickDirective';
import call from './controllers/call';
import resourceManager from './resourceManager';
import Auth from './controllers/auth';
import account from './controllers/account';
import socket from './controllers/socket';
import utils from './utils';
import router from './router';

const app = createApp(App);

const auth = reactive(new Auth());

let components = import.meta.globEager('./globals/*.vue'); // To get each component inside globals folder

for (let path in components) {
	let component = components[path];
	let name = path.replace('./globals/', '').replace('.vue', '');
	app.component(name, component.default || component);
}

app.use(resourceManager);
app.use(utils);
app.use(router);
app.directive('on-outside-click', outsideClickDirective);

app.provide('$call', call);

// Hack to get $auth working, should be refactored later
app.config.globalProperties.$auth = auth;
// Actually, provide-inject is recommended to be used
app.provide('$auth', auth);

app.provide('$account', account);
app.provide('$socket', socket);

// global accessor to expose switchToTeam method
window.$account = account;

app.config.productionTip = false;

app.mount('#app');

app.config.errorHandler = (error, vm) => {
	if (vm) {
		// console.log(vm)
		console.log(inject('$notify'));
		inject('$notify')({
			icon: 'x',
			title: 'An error occurred',
			message: error.messages?.join('\n'),
			color: 'red'
		});
	}
	console.error(error);
};
