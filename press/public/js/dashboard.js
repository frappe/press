import Vue from 'vue/dist/vue.js';

import DashboardRoot from "./DashboardRoot.vue";
s

new Vue({
	el: ".dashboard-container",
	template: "<dashboard-root/>",
	components: {
		DashboardRoot,
	}
});
