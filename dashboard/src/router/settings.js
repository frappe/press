export default {
	path: '/settings',
	name: 'SettingsPage',
	component: () =>
		import(/* webpackChunkName: "account" */ '../views/AccountSettings.vue')
};
