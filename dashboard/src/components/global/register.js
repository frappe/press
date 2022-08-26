import {
	Button,
	Alert,
	Badge,
	FeatherIcon,
	Card,
	LoadingIndicator,
	LoadingText,
	Dialog,
	SuccessMessage,
	Spinner,
	Link,
	Input,
	Avatar
} from 'frappe-ui';
import outsideClickDirective from './outsideClickDirective';

let components = import.meta.globEager('./*.vue'); // To get each component inside this folder

export default function registerGlobalComponents(app) {
	app.directive('on-outside-click', outsideClickDirective);

	for (let path in components) {
		let component = components[path];
		let name = path.replace('./', '').replace('.vue', '');
		app.component(name, component.default || component);
	}

	app.component('Button', Button);
	app.component('Alert', Alert);
	app.component('Avatar', Avatar);
	app.component('Badge', Badge);
	app.component('FeatherIcon', FeatherIcon);
	app.component('Card', Card);
	app.component('LoadingIndicator', LoadingIndicator);
	app.component('LoadingText', LoadingText);
	app.component('SuccessMessage', SuccessMessage);
	app.component('Spinner', Spinner);
	app.component('Link', Link);
	app.component('FrappeUIDialog', Dialog);
	app.component('Input', Input);
}

export { components };
