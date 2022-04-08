import App from './App.vue';
import { createApp } from 'vue';
import registerPlugins from './plugins';
import registerRouter from './router/register';
import registerControllers from './controllers/register';
import registerGlobalComponents from './components/global/register';

const app = createApp(App);

registerPlugins(app);
registerGlobalComponents(app);
const { auth, account, saas } = registerControllers(app);
registerRouter(app, auth, account, saas);

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
