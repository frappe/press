import { createApp } from 'vue';
import {
	setConfig,
	frappeRequest,
	pageMetaPlugin,
	resourcesPlugin,
} from 'frappe-ui';
import App from './App.vue';
import router from './router';
import { initSocket } from './socket';
import { subscribeToJobUpdates } from './utils/agentJob';
import { fetchPlans } from './data/plans.js';
import * as Sentry from '@sentry/vue';
import { session } from './data/session.js';
import { unreadNotificationsCount } from './data/notifications.js';
import registerGlobalComponents from './components/global/register';
import './vendor/posthog.js';

const request = (options) => {
	const _options = options || {};
	_options.headers = options.headers || {};
	const currentTeam =
		localStorage.getItem('current_team') || window.default_team;
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

	registerGlobalComponents(app);

	socket = initSocket();
	app.config.globalProperties.$socket = socket;
	window.$socket = socket;
	subscribeToJobUpdates(socket);
	if (session.isLoggedIn) {
		fetchPlans();
		session.userPermissions.fetch();
		unreadNotificationsCount.fetch();
	}

	if (window.press_dashboard_sentry_dsn.includes('https://')) {
		Sentry.init({
			app,
			dsn: window.press_dashboard_sentry_dsn,
			integrations: [
				Sentry.browserTracingIntegration({ router }),
				Sentry.replayIntegration({
					maskAllText: false,
					blockAllMedia: false,
				}),
				Sentry.thirdPartyErrorFilterIntegration({
					// Specify the application keys that you specified in the Sentry bundler plugin
					filterKeys: ['press-dashboard'],

					// Defines how to handle errors that contain third party stack frames.
					// Possible values are:
					// - 'drop-error-if-contains-third-party-frames'
					// - 'drop-error-if-exclusively-contains-third-party-frames'
					// - 'apply-tag-if-contains-third-party-frames'
					// - 'apply-tag-if-exclusively-contains-third-party-frames'
					behaviour: 'apply-tag-if-contains-third-party-frames',
				}),
			],
			tracesSampleRate: 1.0,
			replaysSessionSampleRate: 0.1,
			replaysOnErrorSampleRate: 1.0,
			beforeSend(event, hint) {
				const ignoreErrors = [
					// /api\/method\/press.api.client/,
					// /dynamically imported module/,
					// /NetworkError when attempting to fetch resource/,
					// /Failed to fetch/,
					// /Load failed/,
					// /frappe is not defined/,
					// /Cannot read properties of undefined \(reading 'exc_type'\)/,
					// /Failed to execute 'transaction' on 'IDBDatabase': The database connection is closing/,
					// /Importing a module script failed./,
					// /o is undefined/,
					// /undefined is not an object \(evaluating 'o.exc_type'\)/,
					// /e is not defined/,
					// /Cannot set property ethereum of #<Window> which has only a getter/,
					// /Can't find variable: ResizeObserver/,
					// /Method not found/,
					// /Menu caption text is required/,
					// /Internal error opening backing store for indexedDB.open/,
				];
				const ignoreErrorTypes = [
					// 'BuildValidationError',
					// 'ValidationError',
					// 'PermissionError',
					// 'SecurityException',
					// 'AAAARecordExists',
					// 'AuthenticationError',
					// 'RateLimitExceededError',
					// 'InsufficientSpaceOnServer',
					// 'ConflictingDNSRecord',
					// 'MultipleARecords',
				];
				const error = hint.originalException;

				if (
					error?.name === 'DashboardError' ||
					ignoreErrorTypes.includes(error?.exc_type) ||
					(error?.message && ignoreErrors.some((re) => re.test(error.message)))
				) {
					return null;
				}

				return event;
			},
			logErrors: true,
		});

		Sentry.setTag('team', localStorage.getItem('current_team'));
	}

	if (
		window.press_frontend_posthog_project_id &&
		window.press_frontend_posthog_host &&
		window.posthog
	) {
		window.posthog.init(window.press_frontend_posthog_project_id, {
			api_host: window.press_frontend_posthog_host,
			person_profiles: 'identified_only',
			autocapture: false,
			disable_session_recording: true,
			session_recording: {
				maskAllInputs: true,
				maskInputFn: (text, element) => {
					if (element?.dataset['record'] === 'true') {
						return text;
					}
					return '*'.repeat(text.trim().length);
				},
			},
		});
	} else {
		// unset posthog if not configured
		window.posthog = undefined;
	}

	importGlobals().then(() => {
		app.mount('#app');
	});
});

function getInitialData() {
	if (import.meta.env.DEV) {
		return frappeRequest({
			url: '/api/method/press.www.dashboard.get_context_for_dev',
		}).then((values) => Object.assign(window, values));
	} else {
		return Promise.resolve();
	}
}

function importGlobals() {
	return import('./globals.ts').then((globals) => {
		app.use(globals.default);
	});
}
