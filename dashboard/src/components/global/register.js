import {
	Button,
	FeatherIcon,
	Tooltip,
	LoadingIndicator,
	LoadingText,
	Dialog,
	Link,
	Input,
	Avatar,
	GreenCheckIcon,
	Dropdown,
	FormControl,
	ErrorMessage,
	Autocomplete
} from 'frappe-ui';
import outsideClickDirective from './outsideClickDirective';

let components = import.meta.glob('./*.vue', { eager: true }); // To get each component inside this folder

let globalFrappeUIComponents = {
	Button,
	Avatar,
	FeatherIcon,
	Tooltip,
	LoadingIndicator,
	LoadingText,
	Link,
	Dialog,
	Input,
	GreenCheckIcon,
	Dropdown,
	FormControl,
	ErrorMessage,
	Autocomplete
};

export default function registerGlobalComponents(app) {
	app.directive('on-outside-click', outsideClickDirective);

	for (let path in components) {
		let component = components[path];
		let name = path.replace('./', '').replace('.vue', '');
		app.component(name, component.default || component);
	}

	for (let key in globalFrappeUIComponents) {
		app.component(key, globalFrappeUIComponents[key]);
	}
}

export { components };
