import Vue from 'vue';
import App from './App.vue';
import './registerServiceWorker';
import './globals';
import router from './router';

Vue.config.productionTip = false;
Vue.config.errorHandler = (error, vm) => {
	vm.$notify({
		icon: 'x',
		title: 'An error occurred',
		message: error.messages.join('\n'),
		color: 'red'
	});
	console.error(error);
};

new Vue({
	router,
	render: h => h(App)
}).$mount('#app');
