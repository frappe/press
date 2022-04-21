import outsideClickDirective from './outsideClickDirective';

let components = import.meta.globEager('./*.vue'); // To get each component inside this folder

export default function registerGlobalComponents(app) {
	app.directive('on-outside-click', outsideClickDirective);

	for (let path in components) {
		let component = components[path];
		let name = path.replace('./', '').replace('.vue', '');
		app.component(name, component.default || component);
	}
}

export { components };
