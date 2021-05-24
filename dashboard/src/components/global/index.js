import Vue from 'vue';
let components = import.meta.globEager('./*.vue');

for (let path in components) {
	let component = components[path];
	let name = path.replace('./', '').replace('.vue', '');
	Vue.component(name, component.default || component);
}
