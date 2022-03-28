import Vue from 'vue';

export default new Vue({
	data() {
		return {
			isLoggedInSaas: null
		};
	},
	methods: {
		async switchToSaas(site) {
			localStorage.removeItem('current_saas_site');
			localStorage.setItem('current_saas_site', site);
			window.location.reload();
		}
	}
});
