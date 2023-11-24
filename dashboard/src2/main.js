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

setConfig('resourceFetcher', frappeRequest);
setConfig('defaultListUrl', 'press.api.client.get_list');
setConfig('defaultDocGetUrl', 'press.api.client.get');
setConfig('defaultDocInsertUrl', 'press.api.client.insert');
setConfig('defaultRunDocMethodUrl', 'press.api.client.run_doc_method');
// setConfig('defaultDocUpdateUrl', 'press.api.list.set_value');
// setConfig('defaultDocDeleteUrl', 'press.api.list.delete');

let app = createApp(App);
app.use(router);
app.use(resourcesPlugin);
app.use(pageMetaPlugin);

let socket;

getInitialData().then(() => {
	socket = initSocket();
	app.config.globalProperties.$socket = socket;
	window.$socket = socket;
	app.mount('#app');
});

function getInitialData() {
	if (import.meta.env.DEV) {
		return frappeRequest({
			url: '/api/method/press.www.dashboard.get_context_for_dev'
		})
			.then(values => Object.assign(window, values))
			.then(importGlobals);
	} else {
		return importGlobals();
	}
}

function importGlobals() {
	return import('./globals.js').then(globals => {
		app.use(globals.default);
	});
}
