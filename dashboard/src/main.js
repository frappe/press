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
const { auth, account, saas } = registerControllers(app);
registerRouter(app, auth, account, saas);

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
