import utils from './utils';
import resourceManager from './resourceManager';

export default function registerPlugins(app) {
	app.use(resourceManager);
	app.use(utils);
}
