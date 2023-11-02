import App from './App.vue';
import { createApp } from 'vue';
import registerPlugins from './plugins';
import registerRouter from './router/register';
import registerControllers from './controllers/register';
import registerGlobalComponents from './components/global/register';
import * as Sentry from '@sentry/vue';
import posthog from 'posthog-js';
import { BrowserTracing } from '@sentry/tracing';
import router from './router/index';
import dayjs from 'dayjs';
import { notify } from '@/utils/toast';
import {
	setConfig,
	frappeRequest,
	pageMetaPlugin,
	resourcesPlugin
} from 'frappe-ui';

const app = createApp(App);
let request = options => {
	let _options = options || {};
	_options.headers = options.headers || {};
	let currentTeam = localStorage.getItem('current_team');
	if (currentTeam) {
		_options.headers['X-Press-Team'] = currentTeam;
	}
	return frappeRequest(_options);
};
setConfig('resourceFetcher', request);
app.use(resourcesPlugin);
app.use(pageMetaPlugin);

registerPlugins(app);
registerGlobalComponents(app);
const { auth, account } = registerControllers(app);
registerRouter(app, auth, account);

// sentry
if (window.press_frontend_sentry_dsn.includes('https://')) {
	Sentry.init({
		app,
		dsn: window.press_frontend_sentry_dsn,
		integrations: [
			new BrowserTracing({
				routingInstrumentation: Sentry.vueRouterInstrumentation(router),
				tracingOrigins: ['localhost', /^\//]
			})
		],
		logErrors: true,
		tracesSampleRate: 1.0
	});
}

// posthog
if (window.press_frontend_posthog_host.includes('https://')) {
	try {
		posthog.init(window.press_frontend_posthog_project_id, {
			api_host: window.press_frontend_posthog_host,
			autocapture: false,
			capture_pageview: false,
			capture_pageleave: false,
			advanced_disable_decide: true
		});
		window.posthog = posthog;
	} catch (e) {
		console.trace('Failed to initialize telemetry', e);
	}
}

app.mount('#app');

app.config.globalProperties.$dayjs = dayjs;
app.config.errorHandler = (error, instance) => {
	if (instance) {
		const errorMessage = error.message || error.messages?.join('\n');
		notify({
			icon: 'x',
			title: 'An error occurred',
			message: errorMessage,
			color: 'red'
		});
	}
	console.error(error);
};
