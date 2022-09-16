import {
	Button,
	Alert,
	Badge,
	FeatherIcon,
	Card,
	Tooltip,
	LoadingIndicator,
	LoadingText,
	Dialog,
	SuccessMessage,
	Spinner,
	Link,
	Input,
	Avatar,
	pageMeta
} from 'frappe-ui';
import outsideClickDirective from './outsideClickDirective';

let components = import.meta.globEager('./*.vue'); // To get each component inside this folder

let globalFrappeUIComponents = {
	Button,
	Alert,
	Avatar,
	Badge,
	FeatherIcon,
	Card,
	Tooltip,
	LoadingIndicator,
	LoadingText,
	SuccessMessage,
	Spinner,
	Link,
	FrappeUIDialog: Dialog,
	Input
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

	// Plugin
	app.use(pageMeta);
}

export { components };
