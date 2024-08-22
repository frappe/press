import { toast } from 'vue-sonner';
import { dayjsLocal } from './utils/dayjs';
import { session } from './data/session';
import theme from '../tailwind.theme.json';
import { debounce } from 'frappe-ui';
import { getTeam } from './data/team';
import * as formatters from './utils/format';
import { getPlatform, isMobile } from './utils/device';

export default function globals(app) {
	app.config.globalProperties.$session = session;
	app.config.globalProperties.$team = session.user ? getTeam() : null;
	app.config.globalProperties.$toast = toast;
	app.config.globalProperties.$dayjs = dayjsLocal;
	app.config.globalProperties.$theme = theme;
	app.config.globalProperties.$platform = getPlatform();
	app.config.globalProperties.$format = formatters;
	app.config.globalProperties.$log = console.log;
	app.config.globalProperties.$debounce = debounce;
	app.config.globalProperties.$isMobile = isMobile();

	// legacy globals for old dashboard
	// TODO: remove later
	app.config.globalProperties.formatBytes = formatters.bytes;
	app.config.globalProperties.$planTitle = formatters.planTitle;
	app.config.globalProperties.$plural = formatters.plural;
}
