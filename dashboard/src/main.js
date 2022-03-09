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

let components = import.meta.globEager('./components/global/*.vue'); // To get each component inside globals folder

for (let path in components) {
	let component = components[path];
	let name = path.replace('./components/global/', '').replace('.vue', '');
	app.component(name, component.default || component);
}

app.use(resourceManager);
app.use(utils);
app.use(router);
app.directive('on-outside-click', outsideClickDirective);

app.config.globalProperties.$call = call;
app.provide('$call', call);

// Hack to get $auth working, should be refactored later
app.config.globalProperties.$auth = auth;
// Actually, provide-inject is recommended to be used
app.provide('$auth', auth);

app.config.globalProperties.$account = account;
app.config.globalProperties.$socket = socket;
app.provide('$account', account);
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
