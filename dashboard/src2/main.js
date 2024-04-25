import { createApp } from 'vue';
import {
	setConfig,
	frappeRequest,
	pageMetaPlugin,
	resourcesPlugin
} from 'frappe-ui';
import App from './App.vue';
import router from './router';
import { initSocket } from './socket';
import { subscribeToJobUpdates } from './utils/agentJob';
import { fetchPlans } from './data/plans.js';

let request = options => {
	let _options = options || {};
	_options.headers = options.headers || {};
	let currentTeam = localStorage.getItem('current_team') || window.default_team;
	if (currentTeam) {
		_options.headers['X-Press-Team'] = currentTeam;
	}
	return frappeRequest(_options);
};
setConfig('resourceFetcher', request);
setConfig('defaultListUrl', 'press.api.client.get_list');
setConfig('defaultDocGetUrl', 'press.api.client.get');
setConfig('defaultDocInsertUrl', 'press.api.client.insert');
setConfig('defaultRunDocMethodUrl', 'press.api.client.run_doc_method');
setConfig('defaultDocUpdateUrl', 'press.api.client.set_value');
setConfig('defaultDocDeleteUrl', 'press.api.client.delete');

let app;
let socket;

getInitialData().then(() => {
	app = createApp(App);
	app.use(router);
	app.use(resourcesPlugin);
	app.use(pageMetaPlugin);

	socket = initSocket();
	app.config.globalProperties.$socket = socket;
	window.$socket = socket;
	subscribeToJobUpdates(socket);
	fetchPlans();

	importGlobals().then(() => {
		app.mount('#app');
	});
});

function getInitialData() {
	if (import.meta.env.DEV) {
		return frappeRequest({
			url: '/api/method/press.www.dashboard.get_context_for_dev'
		}).then(values => Object.assign(window, values));
	} else {
		return Promise.resolve();
	}
}

function importGlobals() {
	return import('./globals.ts').then(globals => {
		app.use(globals.default);
	});
}
