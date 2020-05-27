import Vue from 'vue';
import PortalVue from 'portal-vue';
import '@/components/global';
import outsideClickDirective from '@/components/global/outsideClickDirective';
import call from './controllers/call';
import resourceManager from './resourceManager';
import auth from './controllers/auth';
import account from './controllers/account';
import socket from './controllers/socket';

Vue.use(PortalVue);
Vue.use(resourceManager);
Vue.directive('on-outside-click', outsideClickDirective);

Vue.prototype.$call = call;
Vue.prototype.$auth = auth;
Vue.prototype.$account = account;
Vue.prototype.$account = account;
Vue.prototype.$socket = socket;

Vue.prototype.$plural = function(number, singular, plural) {
	if (number === 1) {
		return singular;
	}
	return plural;
};
