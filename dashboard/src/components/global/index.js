import Vue from 'vue';

const requireComponent = require.context('./', true, /\w+\.(vue)$/);

requireComponent.keys().forEach(fileName => {
	const componentConfig = requireComponent(fileName);

	let match = fileName.match(/\.\/(\w+).vue/);
	let [, componentName] = match || [];

	if (componentName) {
		Vue.component(componentName, componentConfig.default || componentConfig);
	}
});
