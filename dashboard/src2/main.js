import { createApp } from 'vue';
import { toast } from 'vue-sonner';
import {
	setConfig,
	frappeRequest,
	pageMetaPlugin,
	resourcesPlugin
} from 'frappe-ui';
import App from './App.vue';
import router from './router';
import dayjs from './utils/dayjs';
import session from './data/session';
import theme from '../tailwind.theme.json';

setConfig('resourceFetcher', frappeRequest);
setConfig('defaultListUrl', 'press.api.list.get');

let app = createApp(App);
app.use(router);
app.use(resourcesPlugin);
app.use(pageMetaPlugin);

app.config.globalProperties.$session = session;
app.config.globalProperties.$toast = toast;
app.config.globalProperties.$dayjs = dayjs;
app.config.globalProperties.$theme = theme;

fetchTeam().then(() => {
	app.mount('#app');
});

function fetchTeam() {
	return import('./data/team.js');
}

// import('./data/team.js').then(() => {
// 	app.mount('#app');
// });
