import Vue from 'vue';
import '@/components/global';
import outsideClickDirective from '@/components/global/outsideClickDirective';
import call from './controllers/call';
import resourceManager from './resourceManager';
import auth from './controllers/auth';
import account from './controllers/account';
import socket from './controllers/socket';
import utils from './utils';

Vue.use(resourceManager);
Vue.use(utils);
Vue.directive('on-outside-click', outsideClickDirective);

Vue.prototype.$call = call;
Vue.prototype.$auth = auth;
Vue.prototype.$account = account;
Vue.prototype.$account = account;
Vue.prototype.$socket = socket;

// global accessor to expose switchToTeam method
window.$account = account;
