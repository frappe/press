import {
	Button,
	FeatherIcon,
	Tooltip,
	LoadingIndicator,
	LoadingText,
	Dialog,
	Input,
	Avatar,
	Dropdown,
	FormControl,
	ErrorMessage,
	Autocomplete,
	Spinner,
} from 'frappe-ui';
import { GreenCheckIcon } from 'frappe-ui/icons';
import outsideClickDirective from './outsideClickDirective';
import Link from '../Link.vue';

let components = import.meta.glob('./*.vue', { eager: true }); // To get each component inside this folder

let globalFrappeUIComponents = {
	Button,
	Avatar,
	FeatherIcon,
	Tooltip,
	LoadingIndicator,
	LoadingText,
	Dialog,
	Input,
	GreenCheckIcon,
	Dropdown,
	FormControl,
	ErrorMessage,
	Autocomplete,
	Spinner,
	Link,
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
