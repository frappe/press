import { createApp } from 'vue';
import App from './App.vue';
import router from './router';

import {
	setConfig,
	frappeRequest,
	pageMetaPlugin,
	resourcesPlugin
} from 'frappe-ui';
import session from './data/session';

setConfig('resourceFetcher', frappeRequest);
setConfig('defaultListUrl', 'press.api.list.get');

let app = createApp(App);
app.use(router);
app.use(resourcesPlugin);
app.use(pageMetaPlugin);

app.config.globalProperties.$session = session;

fetchTeam().then(() => {
	app.mount('#app');
});

function fetchTeam() {
	return import('./data/team.js');
}

// import('./data/team.js').then(() => {
// 	app.mount('#app');
// });
