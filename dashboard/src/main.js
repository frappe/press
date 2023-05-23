import App from './App.vue';
import { createApp } from 'vue';
import registerPlugins from './plugins';
import registerRouter from './router/register';
import registerControllers from './controllers/register';
import registerGlobalComponents from './components/global/register';
import * as Sentry from '@sentry/vue';
import { BrowserTracing } from '@sentry/tracing';
import router from './router/index';
import dayjs from 'dayjs';

const app = createApp(App);

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
if (window.posthog_keys.posthog_project_id != undefined &&
		window.posthog_keys.posthog_host != undefined) {

	!function(t,e){var o,n,p,r;e.__SV||(window.posthog=e,e._i=[],e.init=function(i,s,a){function g(t,e){var o=e.split(".");2==o.length&&(t=t[o[0]],e=o[1]),t[e]=function(){t.push([e].concat(Array.prototype.slice.call(arguments,0)))}}(p=t.createElement("script")).type="text/javascript",p.async=!0,p.src=s.api_host+"/static/array.js",(r=t.getElementsByTagName("script")[0]).parentNode.insertBefore(p,r);var u=e;for(void 0!==a?u=e[a]=[]:a="posthog",u.people=u.people||[],u.toString=function(t){var e="posthog";return"posthog"!==a&&(e+="."+a),t||(e+=" (stub)"),e},u.people.toString=function(){return u.toString(1)+".people (stub)"},o="capture identify alias people.set people.set_once set_config register register_once unregister opt_out_capturing has_opted_out_capturing opt_in_capturing reset isFeatureEnabled onFeatureFlags".split(" "),n=0;n<o.length;n++)g(u,o[n]);e._i.push([i,s,a])},e.__SV=1)}(document,window.posthog||[]);

	try {
		posthog.init(window.posthog_keys.posthog_project_id, {
			api_host: window.posthog_keys.posthog_host,
			autocapture: false,
			capture_pageview: false,
			capture_pageleave: false,
			advanced_disable_decide: true
		});
	} catch (e) {
		console.trace('Failed to initialize telemetry', e);
	}
}

app.mount('#app');

app.config.globalProperties.$dayjs = dayjs;
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
