import Vue from 'vue';
import PortalVue from 'portal-vue';
import '@/components/global';
import outsideClickDirective from '@/components/global/outsideClickDirective';
import store from './store';
import call from './call';

Vue.use(PortalVue);
Vue.directive('on-outside-click', outsideClickDirective);
Vue.prototype.$store = store;
Vue.prototype.$call = call;
Vue.prototype.$plural = function(number, singular, plural) {
	if (number === 1) {
		return singular;
	}
	return plural;
};
